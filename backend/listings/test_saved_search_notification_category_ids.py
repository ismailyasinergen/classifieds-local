from django.test import TestCase

from categories.models import Category
from listings.saved_search_notifications import _category_ids_for_slug


class SavedSearchNotificationCategoryIdsTests(TestCase):
    def test_category_ids_for_slug_returns_empty_list_for_falsy_inputs(self):
        self.assertEqual(_category_ids_for_slug(None), [])
        self.assertEqual(_category_ids_for_slug(""), [])
        self.assertEqual(_category_ids_for_slug("   "), [])

    def test_category_ids_for_slug_returns_empty_list_for_unknown_slug(self):
        self.assertEqual(_category_ids_for_slug("non-existent-slug"), [])

    def test_category_ids_for_slug_returns_root_only_for_category_with_no_children(self):
        root = Category.objects.create(name="Root", slug="root")
        self.assertEqual(_category_ids_for_slug("root"), [root.pk])

    def test_category_ids_for_slug_returns_tree_for_category_with_children(self):
        root = Category.objects.create(name="Root", slug="root")
        child1 = Category.objects.create(name="Child 1", slug="child-1", parent=root)
        child2 = Category.objects.create(name="Child 2", slug="child-2", parent=root)
        grandchild1 = Category.objects.create(name="Grandchild 1", slug="grandchild-1", parent=child1)
        grandchild2 = Category.objects.create(name="Grandchild 2", slug="grandchild-2", parent=child2)

        result = _category_ids_for_slug("root")
        self.assertEqual(len(result), 5)
        self.assertCountEqual(result, [root.pk, child1.pk, child2.pk, grandchild1.pk, grandchild2.pk])

    def test_category_ids_for_slug_prevents_infinite_loop_on_cyclic_hierarchy(self):
        """
        Tests the edge case where the database somehow contains a cyclic category hierarchy.
        This tests the specific logic `child_ids = [pk for pk in child_ids if pk not in category_ids]`
        in `_category_ids_for_slug` which prevents infinite loops during retrieval.
        """
        c1 = Category.objects.create(name="Category 1", slug="c1")
        c2 = Category.objects.create(name="Category 2", slug="c2", parent=c1)
        c3 = Category.objects.create(name="Category 3", slug="c3", parent=c2)

        # Bypass the model clean method which prevents cycles by using update()
        Category.objects.filter(pk=c1.pk).update(parent=c3)

        # Refresh c1 from DB just to be sure (though not strictly necessary for this test)
        c1.refresh_from_db()

        # If cycle detection fails, this would infinite loop
        result = _category_ids_for_slug("c1")

        self.assertEqual(len(result), 3)
        self.assertCountEqual(result, [c1.pk, c2.pk, c3.pk])
