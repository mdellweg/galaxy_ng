from unittest import mock

from django.conf import settings
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.models import auth as auth_models
from pulpcore.app.models.role import GroupRole, Role
from pulpcore.plugin.util import assign_role
from galaxy_ng.app import constants


API_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")

MOCKED_RH_IDENTITY = {
    'entitlements': {
        'insights': {
            'is_entitled': True
        },
        'smart_management': {
            'is_entitled': True
        },
        'openshift': {
            'is_entitled': True
        },
        'hybrid': {
            'is_entitled': True
        }
    },
    'identity': {
        'account_number': '6269497',
        'type': 'User',
        'user': {
            'username': 'ansible-insights',
            'email': 'fabricio.campineiro@bancoamazonia.com.br',
            'first_name': 'Ansible',
            'last_name': 'Insights',
            'is_active': True,
            'is_org_admin': True,
            'is_internal': False,
            'locale': 'en_US'
        },
        'internal': {
            'org_id': '52814875'
        }
    }
}


def get_current_ui_url(namespace, **kwargs):
    return reverse('galaxy:api:ui:{version}:{namespace}'.format(
        version=constants.CURRENT_UI_API_VERSION,
        namespace=namespace
    ), **kwargs)


class BaseTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = self._create_user('test')
        self.client.force_authenticate(user=self.user)

        # Mock RH identity header
        patcher = mock.patch.object(
            access_policy.AccessPolicyBase, "_get_rh_identity", return_value=MOCKED_RH_IDENTITY
        )

        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _create_user(username):
        return auth_models.User.objects.create(username=username)

    @staticmethod
    def _create_group(scope, name, users=None, perms=[]):
        group, _ = auth_models.Group.objects.get_or_create_identity(scope, name)
        if isinstance(users, auth_models.User):
            users = [users]
        group.user_set.add(*users)
        for p in perms:
            assign_role(p, group)
        return group

    @staticmethod
    def _create_namespace(name, groups=None):
        namespace = models.Namespace.objects.create(name=name)
        if isinstance(groups, auth_models.Group):
            groups = [groups]

        groups_to_add = {}
        for group in groups:
            groups_to_add[group] = [
                'galaxy.namespace_owner',
            ]
        namespace.groups = groups_to_add
        return namespace

    @staticmethod
    def _create_partner_engineer_group():
        pe_roles = [
            # namespaces
            'galaxy.namespace_owner',

            # collections
            'galaxy.collection_admin',

            # users
            'galaxy.user_admin',

            # groups
            'galaxy.group_admin',

            # synclists
            'galaxy.synclist_owner',
        ]
        pe_group = auth_models.Group.objects.create(
            name='partner-engineers')

        for role in pe_roles:
            # GroupRole.objects.create(role=Role.objects.get(name=role), group=pe_group)
            assign_role(role, pe_group)
            # Results in:
            #   ValueError: Cannot assign "<Group: partner-engineers>": "UserRole.user" must be a "User" instance.

        return pe_group
