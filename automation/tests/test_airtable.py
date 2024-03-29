import json

import pytest
from unittest import mock

from ..clients import airtable

from .helpers import (
    TEST_ENV,
    MockSecretsClient,
    get_random_string,
    get_random_airtable_id,
    get_random_created_at,
)

#########
# UTILS #
#########


class FooModel(airtable.MetaBaseModel):
    name: str = get_random_string()

    @staticmethod
    def get_valid_statuses():
        return {
            "New",
            "Processed",
        }


FOO = airtable.TableSpec(
    name="foo",
    model_cls=FooModel,
)


TEST_SECRETS_CLIENT = MockSecretsClient(airtable=json.dumps({"api_key": ""}))
TEST_SETTINGS = airtable.AirtableSettings(_env_file=TEST_ENV)


#########
# TESTS #
#########


def test_model_dirty_basic():
    test_model = FooModel(
        state=airtable.BaseModelState.CLEAN,
        id=get_random_airtable_id(),
        created_at=get_random_created_at(),
        name="foo",
        status="New",
    )
    assert test_model.state == airtable.BaseModelState.CLEAN
    test_model.name = "bar"
    assert test_model.state == airtable.BaseModelState.DIRTY
    test_model.name = "foo"
    assert test_model.state == airtable.BaseModelState.CLEAN


def test_model_modified_fields_basic():
    test_model = FooModel(
        state=airtable.BaseModelState.CLEAN,
        id=get_random_airtable_id(),
        created_at=get_random_created_at(),
        status="New",
    )
    assert test_model.state == airtable.BaseModelState.CLEAN
    assert test_model.modified_fields == set()
    test_model.name = "bar"
    assert test_model.state == airtable.BaseModelState.DIRTY
    assert test_model.modified_fields == {"name"}


def test_model_modified_fields_empty_on_new():
    test_model = FooModel(
        state=airtable.BaseModelState.NEW,
        id=get_random_airtable_id(),
        created_at=get_random_created_at(),
        status="New",
    )
    assert test_model.state == airtable.BaseModelState.NEW
    assert test_model.modified_fields == set()
    test_model.name = "bar"
    assert test_model.state == airtable.BaseModelState.NEW
    assert test_model.modified_fields == set()


def test_model_new_invalid_field_error():
    # Control
    FooModel.new(status="New")

    with pytest.raises(RuntimeError):
        FooModel.new(
            id="1",
            status="New",
        )

    with pytest.raises(RuntimeError):
        FooModel.new(
            state=airtable.BaseModelState.CLEAN,
            status="New",
        )


def test_snapshot_basic():
    test_model = FooModel(
        state=airtable.BaseModelState.CLEAN,
        id=get_random_airtable_id(),
        created_at=get_random_created_at(),
        status="New",
    )

    assert test_model.modified_fields == set()

    test_model.name = "bar"

    assert test_model.modified_fields == {"name"}
    assert test_model.to_airtable(modified_only=True)["fields"].keys() == {
        "name"
    }

    test_model.snapshot()
    assert test_model.modified_fields == set()


def test_incompatible_state_errors():
    with mock.patch("airtable.Airtable.insert"), mock.patch(
        "airtable.Airtable.update"
    ):
        client = FOO.get_airtable_client(
            secrets_client=TEST_SECRETS_CLIENT,
            settings=TEST_SETTINGS,
        )

        with pytest.raises(airtable.IncompatibleModelStateError):
            client.insert(
                FooModel(
                    state=airtable.BaseModelState.CLEAN,
                    id=get_random_airtable_id(),
                    created_at=get_random_created_at(),
                    status="New",
                )
            )

        with pytest.raises(airtable.IncompatibleModelStateError):
            client.update(
                FooModel(
                    state=airtable.BaseModelState.NEW,
                    id=None,
                    created_at=None,
                    status="New",
                )
            )


def test_poll_table_basic():
    # TODO: refactor AirtableClient logic more and get rid of the mocks
    with mock.patch(
        f"{airtable.__name__}.AirtableClient.get_all_with_new_status"
    ) as mock_get, mock.patch(
        f"{airtable.__name__}.AirtableClient.update"
    ) as mock_update:
        # Test data
        test_model = FooModel(
            state=airtable.BaseModelState.CLEAN,
            id=get_random_airtable_id(),
            created_at=get_random_created_at(),
            status="New",
        )

        # Callbacks
        def on_new(foo_model):
            assert foo_model.id == test_model.id
            assert foo_model.status == "New"

            foo_model.status = "Processed"

        def on_processed(foo_model):
            assert foo_model.id == test_model.id
            assert foo_model.status == "Processed"

        def on_status_update(record):
            if record.status == "New":
                on_new(record)
            elif record.status == "Processed":
                on_processed(record)

        # Mocks
        def mock_poll():
            if test_model.status != test_model.meta_last_seen_status:
                return [test_model]
            else:
                return []

        mock_get.side_effect = mock_poll
        client = FOO.get_airtable_client(
            secrets_client=TEST_SECRETS_CLIENT,
            settings=TEST_SETTINGS,
        )
        # Test
        poll_res = client.poll_table(on_status_update)

        assert poll_res
        assert test_model.status == "Processed"
        assert test_model.meta_last_seen_status == "New"
        assert mock_update.call_count == 1

        poll_res = client.poll_table(on_status_update)

        assert poll_res
        assert test_model.status == "Processed"
        assert test_model.meta_last_seen_status == "Processed"
        assert mock_update.call_count == 2

        # NOTE that this call should be a no-op
        poll_res = client.poll_table(on_status_update)

        assert poll_res
        assert mock_update.call_count == 2
        assert mock_get.call_count == 3


def test_poll_table_retries():
    """Test the case where all callback calls fail"""
    with mock.patch(
        f"{airtable.__name__}.AirtableClient.get_all_with_new_status"
    ) as mock_get, mock.patch(
        f"{airtable.__name__}.AirtableClient.update"
    ) as mock_update:
        test_model = FooModel(
            state=airtable.BaseModelState.CLEAN,
            id=get_random_airtable_id(),
            created_at=get_random_created_at(),
            status="New",
        )

        mock_get.side_effect = lambda: [test_model]

        # NOTE that we have to create the mock from a no-op lambda to set magic
        # attributes used for logging in `poll_table`
        on_new_mock = mock.MagicMock(
            spec=lambda: None, side_effect=Exception("Fuuuuuu")
        )

        def on_status_update(record):
            if record.status == "New":
                on_new_mock(record)

        client = FOO.get_airtable_client(
            secrets_client=TEST_SECRETS_CLIENT, settings=TEST_SETTINGS
        )
        poll_res = client.poll_table(on_status_update, max_num_retries=3)

        assert not poll_res
        assert test_model.status == "New"
        assert test_model.meta_last_seen_status == "New"
        assert mock_update.call_count == 1
        assert on_new_mock.call_count == 3


def test_poll_table_retries_transient():
    """Test the case where all but the last callback calls fail"""
    with mock.patch(
        f"{airtable.__name__}.AirtableClient.get_all_with_new_status"
    ) as mock_get, mock.patch(
        f"{airtable.__name__}.AirtableClient.update"
    ) as mock_update:
        test_model = FooModel(
            state=airtable.BaseModelState.CLEAN,
            id=get_random_airtable_id(),
            created_at=get_random_created_at(),
            status="New",
        )

        mock_get.side_effect = lambda: [test_model]

        # NOTE that we have to create the mock from a no-op lambda to set magic
        # attributes used for logging in `poll_table`
        on_new_mock = mock.MagicMock(
            spec=lambda: None,
            side_effect=[
                Exception("Fuuuuuu"),
                Exception("Fuuuuuu"),
                None,
            ],
        )

        def on_status_update(record):
            if record.status == "New":
                on_new_mock(record)

        client = FOO.get_airtable_client(
            secrets_client=TEST_SECRETS_CLIENT, settings=TEST_SETTINGS
        )
        poll_res = client.poll_table(on_status_update, max_num_retries=3)

        assert poll_res
        assert test_model.status == "New"
        assert test_model.meta_last_seen_status == "New"
        assert mock_update.call_count == 1
        assert on_new_mock.call_count == 3
