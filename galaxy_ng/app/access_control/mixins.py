from django.conf import settings
from django.db import transaction
from django.db.models import Q
# from guardian.shortcuts import get_groups_with_perms, assign_perm, remove_perm
from pulpcore.app.role_util import assign_role, remove_role, get_groups_with_perms
from pulpcore.app.models.role import GroupRole
from django.contrib.contenttypes.models import ContentType

from django_lifecycle import hook


def tmp_get_groups_with_perms_attched_roles(obj):
    groups = get_groups_with_perms(obj)
    ctype = ContentType.objects.get_for_model(obj)

    result = {}
    for group in groups:
        group_roles = GroupRole.objects.filter(
            Q(object_id=None) | Q(content_type=ctype, object_id=obj.pk)
        )

        result[group] = [gr.role.name for gr in group_roles]

    return result


class GroupModelPermissionsMixin:
    _groups = None

    @property
    def groups(self):
        return tmp_get_groups_with_perms_attched_roles(self)

    @groups.setter
    def groups(self, groups):
        self._set_groups(groups)

    @transaction.atomic
    def _set_groups(self, groups):
        # guardian doesn't allow adding permissions to objects that haven't been
        # saved. When creating new objects, save group data to _groups where it
        # can be picked up by the post save hook.
        if self._state.adding:
            self._groups = groups
        else:
            current_groups = tmp_get_groups_with_perms_attched_roles(self)
            for group in current_groups:
                for perm in current_groups[group]:
                    remove_role(perm, group, self)

            for group in groups:
                for perm in groups[group]:
                    assign_role(perm, group, self)

    @hook('after_save')
    def set_object_groups(self):
        if self._groups:
            self._set_groups(self._groups)


class UnauthenticatedCollectionAccessMixin:
    def unauthenticated_collection_access_enabled(self, request, view, action):
        return settings.GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS
