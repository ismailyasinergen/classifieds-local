from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, ListView

from listings.models import Listing

from .forms import ListingMessageForm
from .models import ListingMessage


def build_conversation_threads(user, mode="all"):
    if mode == "sent":
        queryset = ListingMessage.objects.filter(sender=user)
    else:
        queryset = ListingMessage.objects.filter(
            Q(sender=user) | Q(recipient=user)
        )

    queryset = (
        queryset
        .select_related("listing", "sender", "recipient")
        .order_by("-created_at")
    )

    grouped = {}

    for message in queryset:
        other_user = message.recipient if message.sender == user else message.sender
        key = (message.listing_id, other_user.id)

        if key not in grouped:
            unread_count = ListingMessage.objects.filter(
                listing=message.listing,
                sender=other_user,
                recipient=user,
                is_read=False,
            ).count()

            grouped[key] = SimpleNamespace(
                latest_message=message,
                listing=message.listing,
                other_user=other_user,
                unread_count=unread_count,
            )

    return list(grouped.values())


class InboxView(LoginRequiredMixin, ListView):
    template_name = "conversations/inbox.html"
    context_object_name = "threads"
    paginate_by = 20

    def get_queryset(self):
        return build_conversation_threads(self.request.user, mode="all")


class SentMessagesView(LoginRequiredMixin, ListView):
    template_name = "conversations/sent.html"
    context_object_name = "threads"
    paginate_by = 20

    def get_queryset(self):
        return build_conversation_threads(self.request.user, mode="sent")


class ListingMessageCreateView(LoginRequiredMixin, CreateView):
    model = ListingMessage
    form_class = ListingMessageForm
    template_name = "conversations/message_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.listing = get_object_or_404(
            Listing.objects.select_related("owner"),
            pk=kwargs["pk"],
            status=Listing.Status.APPROVED,
        )

        if self.listing.owner == request.user:
            messages.warning(request, "You cannot message yourself about your own listing.")
            return redirect(self.listing.get_absolute_url())

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.listing = self.listing
        form.instance.sender = self.request.user
        form.instance.recipient = self.listing.owner

        messages.success(self.request, "Message sent to seller.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_thread_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listing"] = self.listing
        context["page_title"] = "Contact Seller"
        return context


@login_required
def message_thread_view(request, pk):
    selected_message = get_object_or_404(
        ListingMessage.objects.select_related("listing", "sender", "recipient"),
        pk=pk,
    )

    if request.user not in [selected_message.sender, selected_message.recipient]:
        messages.warning(request, "You cannot view that message thread.")
        return redirect("conversations:inbox")

    other_user = (
        selected_message.sender
        if selected_message.recipient == request.user
        else selected_message.recipient
    )

    thread_messages = (
        ListingMessage.objects
        .select_related("listing", "sender", "recipient")
        .filter(listing=selected_message.listing)
        .filter(
            Q(sender=request.user, recipient=other_user)
            | Q(sender=other_user, recipient=request.user)
        )
        .order_by("created_at")
    )

    thread_messages.filter(recipient=request.user, is_read=False).update(is_read=True)

    form = ListingMessageForm()

    return render(
        request,
        "conversations/thread.html",
        {
            "selected_message": selected_message,
            "other_user": other_user,
            "thread_messages": thread_messages,
            "form": form,
            "page_title": "Message Thread",
        },
    )


@login_required
def message_reply_view(request, pk):
    selected_message = get_object_or_404(
        ListingMessage.objects.select_related("listing", "sender", "recipient"),
        pk=pk,
    )

    if request.user not in [selected_message.sender, selected_message.recipient]:
        messages.warning(request, "You cannot reply to that message thread.")
        return redirect("conversations:inbox")

    other_user = (
        selected_message.sender
        if selected_message.recipient == request.user
        else selected_message.recipient
    )

    if request.method != "POST":
        return redirect("conversations:thread", pk=selected_message.pk)

    form = ListingMessageForm(request.POST)

    if form.is_valid():
        reply = form.save(commit=False)
        reply.listing = selected_message.listing
        reply.sender = request.user
        reply.recipient = other_user
        reply.save()

        messages.success(request, "Reply sent.")
        return redirect("conversations:thread", pk=reply.pk)

    thread_messages = (
        ListingMessage.objects
        .select_related("listing", "sender", "recipient")
        .filter(listing=selected_message.listing)
        .filter(
            Q(sender=request.user, recipient=other_user)
            | Q(sender=other_user, recipient=request.user)
        )
        .order_by("created_at")
    )

    return render(
        request,
        "conversations/thread.html",
        {
            "selected_message": selected_message,
            "other_user": other_user,
            "thread_messages": thread_messages,
            "form": form,
            "page_title": "Message Thread",
        },
    )
