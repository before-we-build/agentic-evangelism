"""Evidence, privacy and no-spend tests for image route planning and Codex status."""

import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/dual-image-pipeline/scripts'
sys.path.insert(0, str(SCRIPTS))
import codex_status
import profiles


NOW = 1000


def route(route_id='codex-images', group='my-account', cap=2):
    return {
        'id': route_id, 'kind': 'host_tool', 'quota_group': group,
        'image_capability': True, 'authorized': True, 'entitlement': 'verified',
        'subscription': {'kind': 'subscription', 'plan': 'plus'},
        'evidence': {'source': 'host_tool', 'checked_at': NOW - 10, 'expires_at': NOW + 1000},
        'limits': {'max_parallel': cap}, 'cost': {'per_request': 0},
        'overage_disabled': True,
    }


def normalize(*routes):
    return profiles.normalize_profiles({'schema_version': 1, 'routes': list(routes)}, now=NOW)


def snapshot(used=20):
    result = codex_status.sanitize(
        {'account': {'type': 'chatgpt', 'planType': 'plus'}},
        {'rateLimits': {'primary': {'usedPercent': used, 'resetsAt': NOW + 300, 'windowDurationMins': 300}}},
        now=NOW,
    )
    result['available'] = True
    return result


class ProfileTests(unittest.TestCase):
    def test_valid_evidence_and_plan_name_do_not_determine_parallelism(self):
        for plan_name in ('free', 'plus', 'pro', 'enterprise', 'unknown'):
            raw = route()
            raw['subscription']['plan'] = plan_name
            raw['limits'] = {}
            actual = normalize(raw)[0]
            self.assertTrue(actual['eligible'], actual['blocked_reasons'])
            self.assertEqual(actual['limits']['max_parallel'], 1)
            self.assertEqual(actual['limits']['initial_parallel'], 1)
            self.assertEqual(raw['limits'], {}, 'validation must not mutate input')

    def test_unverified_access_or_authorization_is_blocked(self):
        for field, value in [('image_capability', False), ('authorized', 1), ('entitlement', 'unknown')]:
            with self.subTest(field=field):
                raw = route()
                raw[field] = value
                self.assertFalse(normalize(raw)[0]['eligible'])

    def test_missing_expired_or_future_evidence_is_blocked(self):
        for evidence in ({}, {'source': 'user_confirmed', 'checked_at': 800, 'expires_at': 1000},
                         {'source': 'user_confirmed', 'checked_at': 1100, 'expires_at': 1200},
                         {'source': 'invented', 'checked_at': 900, 'expires_at': 1200}):
            with self.subTest(evidence=evidence):
                raw = route()
                raw['evidence'] = evidence
                self.assertFalse(normalize(raw)[0]['eligible'])

    def test_api_unknown_cost_and_unverified_free_claim_are_blocked(self):
        raw = route()
        raw['subscription']['kind'] = 'api'
        raw['cost'] = {}
        self.assertFalse(normalize(raw)[0]['eligible'])
        raw['cost'] = {'per_request': 0}
        self.assertFalse(normalize(raw)[0]['eligible'])
        raw['zero_cost_verified'] = True
        self.assertTrue(normalize(raw)[0]['eligible'])

    def test_subscription_zero_cost_requires_confirmed_no_overages(self):
        for value in (None, False, 1, 'true'):
            raw = route()
            raw['overage_disabled'] = value
            self.assertFalse(normalize(raw)[0]['eligible'])

    def test_paid_route_requires_known_approved_budget(self):
        raw = route()
        raw['cost'] = {'per_request': 0.2}
        self.assertFalse(normalize(raw)[0]['eligible'])
        raw['cost']['budget_remaining'] = 1
        self.assertTrue(normalize(raw)[0]['eligible'])

    def test_shared_account_capacity_is_not_added_twice(self):
        normalized = normalize(route('a', 'shared', 4), route('b', 'shared', 2), route('c', 'separate', 3))
        self.assertEqual(profiles.plan(normalized, 20)['eligible_capacity_ceiling'], 5)
        self.assertEqual(profiles.plan(normalized, 4)['eligible_capacity_ceiling'], 4)

    def test_plan_drops_nested_secrets_and_does_not_execute_commands(self):
        raw = route()
        for field in ('subscription', 'evidence', 'limits', 'cost'):
            raw[field]['token'] = 'sk-private-secret'
            raw[field]['email'] = 'private@example.com'
        raw['command'] = ['sh', '-c', 'touch /never-execute-this']
        raw['limits']['quota_windows'] = [{'used_percent': 5, 'resets_at': 1400,
                                          'window_minutes': 60, 'token': 'sk-private-secret'}]
        normalized = normalize(raw)
        with patch.object(codex_status.subprocess, 'Popen') as popen, patch.object(codex_status.subprocess, 'run') as run:
            result = json.dumps(profiles.plan(normalized, 4))
        popen.assert_not_called()
        run.assert_not_called()
        self.assertNotIn('sk-private-secret', result)
        self.assertNotIn('private@example.com', result)
        self.assertNotIn('never-execute-this', result)

    def test_plan_rejects_private_account_identifiers_and_redacts_bad_labels(self):
        raw = route()
        raw['quota_group'] = 'private@example.com'
        with self.assertRaises(ValueError):
            normalize(raw)
        for label in ('private@example.com', 'sk-private-secret'):
            raw = route()
            raw['subscription']['plan'] = label
            self.assertNotIn(label, json.dumps(profiles.plan(normalize(raw), 2)))

    def test_discovery_never_probes_a_generator_or_claims_entitlement(self):
        with patch.object(profiles.shutil, 'which', side_effect=lambda name: '/bin/' + name), \
                patch.object(codex_status.subprocess, 'Popen') as popen:
            found = profiles.discover()
        popen.assert_not_called()
        self.assertEqual(len(found['candidates']), 3)
        self.assertTrue(all(not item['eligible'] for item in found['candidates']))

    def test_numeric_fields_reject_bools_nonfinite_negative_and_fractional_limits(self):
        for field in ('max_parallel', 'initial_parallel', 'requests_per_minute', 'requests_per_day', 'remaining_requests'):
            for value in (True, '2', float('inf'), float('nan'), -1, 1.5):
                with self.subTest(field=field, value=value):
                    raw = route()
                    raw['limits'][field] = value
                    with self.assertRaises(ValueError):
                        normalize(raw)
        for field in ('per_request', 'budget_remaining'):
            for value in (True, '1', float('inf'), float('nan'), -1):
                raw = route()
                raw['cost'][field] = value
                with self.assertRaises(ValueError):
                    normalize(raw)
        for value in (True, 0, -1, 1.5, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                profiles.plan(normalize(route()), value)

    def test_invalid_schema_and_nested_shapes_fail_cleanly(self):
        with self.assertRaises(ValueError):
            profiles.normalize_profiles({'schema_version': True, 'routes': [route()]}, now=NOW)
        for field, value in [('subscription', []), ('limits', []), ('evidence', []),
                             ('cost', []), ('supports_references', 1), ('kind', [])]:
            raw = route()
            raw[field] = value
            with self.assertRaises(ValueError):
                normalize(raw)
        raw = route()
        raw['limits']['quota_windows'] = [None]
        with self.assertRaises(ValueError):
            normalize(raw)

    def test_conflicting_shared_budget_currencies_are_rejected(self):
        first, second = route('first'), route('second')
        first['cost']['currency'], second['cost']['currency'] = 'USD', 'EUR'
        with self.assertRaisesRegex(ValueError, 'currencies'):
            normalize(first, second)


class FakeProcess:
    def __init__(self, messages):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(''.join(json.dumps(message) + '\n' for message in messages))
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout):
        return self.returncode


class CodexStatusTests(unittest.TestCase):
    def test_sanitize_never_outputs_credentials_email_or_account_ids(self):
        account = {'account': {'type': 'chatgpt', 'planType': 'plus', 'email': 'private@example.com',
                               'token': 'sk-private-secret', 'id': 'private-account-id'}}
        limits = {'rateLimits': {'primary': {'usedPercent': 10, 'resetsAt': 1200, 'windowDurationMins': 300},
                                 'token': 'sk-private-secret'}, 'accessToken': 'sk-private-secret'}
        result = codex_status.sanitize(account, limits, now=NOW)
        rendered = json.dumps(result)
        self.assertTrue(result['quota_available'])
        self.assertIsNone(result['remaining_requests'])
        self.assertIsNone(result['max_parallel'])
        for private in ('private@example.com', 'sk-private-secret', 'private-account-id'):
            self.assertNotIn(private, rendered)
        account['account']['type'] = 'sk-private-secret'
        account['account']['planType'] = 'private@example.com'
        self.assertIsNone(codex_status.sanitize(account, limits)['account_type'])
        self.assertIsNone(codex_status.sanitize(account, limits)['plan'])

    def test_unknown_model_specific_only_limits_never_imply_quota(self):
        status = codex_status.sanitize({'account': {'type': 'chatgpt', 'planType': 'pro'}},
                                      {'rateLimitsByLimitId': {'codex': {'primary': {
                                          'usedPercent': 1, 'resetsAt': 1200, 'windowDurationMins': 300}}}}, now=NOW)
        status['available'] = True
        self.assertFalse(status['quota_available'])
        raw = route()
        raw['status_source'] = 'codex_app_server'
        codex_status.refresh([raw], status)
        self.assertFalse(normalize(raw)[0]['eligible'])

    def test_schema_plan_labels_are_public_but_never_capacity(self):
        for plan_name in ('prolite', 'self_serve_business_prolite', 'ent26', 'edu_pro'):
            result = codex_status.sanitize({'account': {'type': 'chatgpt', 'planType': plan_name}}, {}, now=NOW)
            self.assertEqual(result['plan'], plan_name)
            self.assertIsNone(result['max_parallel'])
            self.assertFalse(result['quota_available'])

    def test_invalid_and_partial_quota_windows_fail_closed(self):
        for value in (True, '10', float('nan'), float('inf'), -1, 101, 10**400):
            status = codex_status.sanitize({'account': {}}, {'rateLimits': {
                'primary': {'usedPercent': 10, 'resetsAt': 1200, 'windowDurationMins': 60},
                'secondary': {'usedPercent': value, 'resetsAt': 1300, 'windowDurationMins': 300}}}, now=NOW)
            self.assertFalse(status['quota_available'])
        for account, limits in [(None, None), ({'account': []}, {'rateLimits': []}), ([], [])]:
            self.assertFalse(codex_status.sanitize(account, limits, now=NOW)['quota_available'])

    def test_failed_status_refresh_blocks_bound_routes_only(self):
        for status in ({'available': False, 'reason': 'error'}, {'available': True, 'account_type': 'apiKey'},
                       {'available': True, 'account_type': 'chatgpt', 'quota_available': False}):
            bound, other = route('bound'), route('other')
            bound['status_source'] = 'codex_app_server'
            codex_status.refresh([bound, other], status)
            self.assertFalse(normalize(bound)[0]['eligible'])
            self.assertTrue(normalize(other)[0]['eligible'])

    def test_refresh_records_quota_without_renewing_image_authorization(self):
        raw = route()
        raw['status_source'] = 'codex_app_server'
        raw['evidence']['expires_at'] = NOW + 50
        original_evidence = copy.deepcopy(raw['evidence'])
        codex_status.refresh([raw], snapshot())
        self.assertEqual(raw['evidence']['expires_at'], NOW + 50)
        self.assertEqual(raw['evidence'], original_evidence)
        self.assertEqual(raw['status_checked_at'], NOW)
        self.assertEqual(raw['status_expires_at'], NOW + 300)
        self.assertEqual(raw['limits']['max_parallel'], 2)
        self.assertNotIn('remaining_requests', raw['limits'])
        self.assertTrue(normalize(raw)[0]['eligible'])
        raw['evidence']['expires_at'] = NOW - 1
        codex_status.refresh([raw], snapshot())
        self.assertFalse(normalize(raw)[0]['eligible'])

    def test_refresh_does_not_renew_numeric_balance_snapshots(self):
        raw = route()
        raw['status_source'] = 'codex_app_server'
        raw['limits']['remaining_requests'] = 3
        raw['cost']['budget_remaining'] = 10
        before = normalize(raw)[0]
        codex_status.refresh([before], snapshot())
        after = normalize(before)[0]
        self.assertEqual(after['limits']['remaining_checked_at'], NOW - 10)
        self.assertEqual(after['cost']['budget_checked_at'], NOW - 10)

    def test_expired_status_is_blocked_even_with_fresh_access_evidence(self):
        raw = route()
        raw['status_checked_at'] = NOW - 100
        raw['status_expires_at'] = NOW
        self.assertFalse(normalize(raw)[0]['eligible'])

    def test_refresh_does_not_upgrade_unverified_image_entitlement(self):
        raw = route()
        raw['status_source'] = 'codex_app_server'
        raw['entitlement'] = 'unknown'
        codex_status.refresh([raw], snapshot())
        self.assertFalse(normalize(raw)[0]['eligible'])

    def test_refresh_never_relabels_api_or_local_billing_as_subscription(self):
        for kind in ('api', 'local'):
            raw = route()
            raw['status_source'] = 'codex_app_server'
            raw['subscription']['kind'] = kind
            original = copy.deepcopy(raw['subscription'])
            codex_status.refresh([raw], snapshot())
            self.assertEqual(raw['subscription'], original)
            self.assertEqual(raw['entitlement'], 'unknown')
            self.assertFalse(normalize(raw)[0]['eligible'])

    def test_exhausted_quota_stays_blocked_even_after_reset_time(self):
        raw = route()
        raw['status_source'] = 'codex_app_server'
        status = snapshot(100)
        status['quota_windows'][0]['resets_at'] = NOW - 1
        codex_status.refresh([raw], status)
        self.assertFalse(normalize(raw)[0]['eligible'])

    def test_probe_launch_failure_returns_generic_nonsecret_error(self):
        with patch.object(codex_status.shutil, 'which', return_value='/bin/codex'), \
                patch.object(codex_status.subprocess, 'Popen', side_effect=OSError('sk-private-secret')):
            result = codex_status.probe()
        self.assertFalse(result['available'])
        self.assertNotIn('sk-private-secret', json.dumps(result))

    def test_mock_rpc_error_is_not_echoed_and_process_is_closed(self):
        process = FakeProcess([{'id': 1, 'result': {}}, {'id': 2, 'error': {
            'message': 'private@example.com sk-private-secret'}}])
        with patch.object(codex_status.shutil, 'which', return_value='/bin/codex'), \
                patch.object(codex_status.subprocess, 'Popen', return_value=process):
            result = codex_status.probe()
        self.assertFalse(result['available'])
        self.assertNotIn('private@example.com', json.dumps(result))
        self.assertNotIn('sk-private-secret', json.dumps(result))
        self.assertTrue(process.stdin.closed)
        self.assertTrue(process.stdout.closed)

    def test_mock_rpc_status_with_unavailable_limits_remains_unknown(self):
        process = FakeProcess([{'id': 1, 'result': {}}, {'id': 2, 'result': {'account': {
            'type': 'chatgpt', 'planType': 'pro', 'email': 'private@example.com'}}},
            {'id': 3, 'error': {'message': 'sk-private-secret'}}])
        with patch.object(codex_status.shutil, 'which', return_value='/bin/codex'), \
                patch.object(codex_status.subprocess, 'Popen', return_value=process):
            result = codex_status.probe()
        self.assertTrue(result['available'])
        self.assertFalse(result['quota_available'])
        self.assertEqual(result['quota_status'], 'request_failed')
        self.assertNotIn('private@example.com', json.dumps(result))
        self.assertNotIn('sk-private-secret', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
