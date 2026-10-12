from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

from accounts.rate_limits import ActionRateLimited
from listings.models import Listing
from moderation.policies import visible_listings
from . import queries, services
from .forms import MessageForm, add_service_errors
from .models import Conversation, Participant, UserBlock
from .policies import can_reply


def private_view(methods):
    def decorate(view):
        @wraps(view)
        def protected(request, *args, **kwargs):
            try:
                if request.method not in methods:
                    response = HttpResponseNotAllowed(methods)
                elif not request.user.is_authenticated:
                    response = login_required(view)(request, *args, **kwargs)
                else:
                    response = view(request, *args, **kwargs)
            except (Conversation.DoesNotExist, Listing.DoesNotExist, Http404):
                response = render(request, "conversations/unavailable.html", {"status": 404}, status=404)
            except PermissionDenied:
                response = render(request, "conversations/unavailable.html", {"status": 403}, status=403)
            response["Cache-Control"] = "private, no-store"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        return protected
    return decorate


def decimal(value, maximum, length):
    if (not isinstance(value, str) or not value or len(value) > length
            or not value.isascii() or not value.isdecimal()):
        raise Http404
    number = int(value)
    if number < 1 or number > maximum:
        raise Http404
    return number


def page_number(request):
    return decimal(request.GET.get("page", "1"), 999999999, 9)


def paginate(rows, size, number):
    try:
        return Paginator(rows, size).page(number)
    except EmptyPage:
        raise Http404


def thread(request, conversation_id):
    # Canonical lookup always precedes page parsing, counts and metadata.
    return queries.conversation_for_actor(actor=request.user, conversation_id=conversation_id)


def history_context(request, conversation):
    number = page_number(request)
    page = paginate(queries.conversation_messages(
        actor=request.user, conversation_id=conversation.pk), 30, number)
    rows = list(reversed(list(page.object_list)))
    return {"conversation": conversation, "page_obj": page, "history_messages": rows,
            "through_message_id": rows[-1].pk if rows else None,
            "latest_sequence": rows[-1].sequence if rows else 0,
            "newest": number == 1}


def detail_response(request, conversation, form=None, status=200):
    context = history_context(request, conversation)
    other_id = conversation.recipient_id if request.user.pk == conversation.initiator_id else conversation.initiator_id
    context.update({
        "form": form if form is not None else MessageForm(),
        "may_reply": can_reply(actor=request.user, conversation=conversation),
        "viewer_state": Participant.objects.get(conversation=conversation, user_id=request.user.pk),
        "own_block": UserBlock.objects.filter(blocker_id=request.user.pk, blocked_id=other_id).exists(),
        "public_listing": visible_listings().filter(pk=conversation.listing_id).exists(),
    })
    return render(request, "conversations/detail.html", context, status=status)


@private_view(["GET"])
def inbox(request):
    archived = request.GET.get("archived") == "1"
    page = paginate(queries.inbox_conversations(actor=request.user, archived=archived), 12, page_number(request))
    return render(request, "conversations/inbox.html", {"page_obj": page, "archived": archived})


@private_view(["GET", "POST"])
def start(request, listing_id):
    if request.method == "GET":
        try:
            listing, conversation = queries.start_context(actor=request.user, listing_id=listing_id)
        except ValidationError:
            return render(request, "conversations/unavailable.html", {"status": 400}, status=400)
        if conversation:
            return redirect("conversations:detail", conversation.pk)
        return render(request, "conversations/start.html", {"listing": listing, "subject": listing.public_revision.title, "form": MessageForm()})
    # Resolve the start policy even when form input is invalid.
    try:
        listing, existing = queries.start_context(actor=request.user, listing_id=listing_id)
    except ValidationError:
        return render(request, "conversations/unavailable.html", {"status": 400}, status=400)
    form = MessageForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            message = services.start_conversation(actor=request.user, listing_id=listing_id, **form.cleaned_data)
            return redirect("conversations:detail", message.conversation_id)
        except ActionRateLimited as error:
            form.add_error(None, error)
            subject = existing.subject if existing else listing.public_revision.title
            response = render(request, "conversations/start.html", {
                "listing": listing, "subject": subject, "form": form}, status=429)
            response["Retry-After"] = str(error.retry_after)
            return response
        except ValidationError as error:
            status = add_service_errors(form, error)
    subject = existing.subject if existing else listing.public_revision.title
    return render(request, "conversations/start.html", {"listing": listing, "subject": subject, "form": form}, status=status)


@private_view(["POST"])
def contact(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    # Known owner denial is 403 even for malformed preference input.
    if listing.owner_id != request.user.pk:
        raise PermissionDenied
    values = request.POST.getlist("enabled")
    if len(values) != 1 or values[0] not in ("0", "1"):
        return render(request, "conversations/unavailable.html", {"status": 400}, status=400)
    services.set_contact_enabled(actor=request.user, listing_id=listing_id, enabled=values[0] == "1")
    return redirect("listings:detail", listing_id)


@private_view(["GET"])
def detail(request, conversation_id):
    return detail_response(request, thread(request, conversation_id))


@private_view(["GET"])
def history(request, conversation_id):
    conversation = thread(request, conversation_id)
    number = page_number(request)
    after = request.GET.get("after_sequence")
    if after is not None:
        after = decimal(after, 9223372036854775807, 19)
        if number == 1 and after == conversation.last_sequence:
            return HttpResponse(status=204)
    return render(request, "conversations/history.html", history_context(request, conversation))


@private_view(["POST"])
def send(request, conversation_id):
    conversation = thread(request, conversation_id)
    form = MessageForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            services.send_message(actor=request.user, conversation_id=conversation.pk, **form.cleaned_data)
            return redirect("conversations:detail", conversation.pk)
        except ActionRateLimited as error:
            form.add_error(None, error)
            response = detail_response(request, conversation, form=form, status=429)
            response["Retry-After"] = str(error.retry_after)
            return response
        except ValidationError as error:
            status = add_service_errors(form, error)
        except PermissionDenied:
            form.add_error(None, "Bu görüşmede şu anda mesaj gönderilemiyor.")
            status = 403
    return detail_response(request, conversation, form=form, status=status)


@private_view(["POST"])
def mark_read(request, conversation_id):
    conversation = thread(request, conversation_id)
    try:
        through = decimal(request.POST.get("through_message_id"), 9223372036854775807, 19)
        services.mark_read(actor=request.user, conversation_id=conversation.pk, through_message_id=through)
    except (Http404, ValidationError):
        return render(request, "conversations/unavailable.html", {"status": 400}, status=400)
    return redirect("conversations:detail", conversation.pk)


@private_view(["POST"])
def archive(request, conversation_id):
    conversation = thread(request, conversation_id)
    services.set_archived(actor=request.user, conversation_id=conversation.pk, archived=True)
    return redirect("conversations:inbox")


@private_view(["POST"])
def unarchive(request, conversation_id):
    conversation = thread(request, conversation_id)
    services.set_archived(actor=request.user, conversation_id=conversation.pk, archived=False)
    return redirect("conversations:detail", conversation.pk)


def change_block(request, conversation_id, blocked):
    conversation = thread(request, conversation_id)
    other_id = conversation.recipient_id if request.user.pk == conversation.initiator_id else conversation.initiator_id
    operation = services.block_user if blocked else services.unblock_user
    operation(actor=request.user, other_user_id=other_id)
    return redirect("conversations:detail", conversation.pk)


@private_view(["POST"])
def block(request, conversation_id):
    return change_block(request, conversation_id, True)


@private_view(["POST"])
def unblock(request, conversation_id):
    return change_block(request, conversation_id, False)
