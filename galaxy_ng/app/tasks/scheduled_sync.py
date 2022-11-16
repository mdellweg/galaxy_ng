from pulpcore.plugin.tasking import dispatch
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.tasks.collections import sync as collection_sync
from pulp_ansible.app.tasks.roles import synchronize as role_sync
from pulp_ansible.app.tasks.git import synchronize as git_sync


def scheduled_sync():
    """This is a scheduled task to regularly schedule repository syncs."""

    for repository in AnsibleRepository.objects.filter(remote__isnull==False):
        # TODO filter on more conditions like labels
        remote = repository.remote
        mirror = True  # IDK

        sync_kwargs = {
            "remote_pk": remote.pk,
            "repository_pk": repository.pk,
            "mirror": mirror,
        }

        if isinstance(remote, RoleRemote):
            sync_func = role_sync
        elif isinstance(remote, CollectionRemote):
            sync_func = collection_sync
            sync_kwargs["optimize"] = serializer.validated_data["optimize"]
        elif isinstance(remote, GitRemote):
            sync_func = git_sync

        dispatch(
            sync_func,
            exclusive_resources=[repository],
            shared_resources=[remote],
            kwargs=sync_kwargs,
        )
