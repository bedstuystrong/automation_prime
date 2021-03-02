import pytest
from unittest import mock

from ..clients import airtable

from .helpers import (
    TEST_CONFIG,
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


def get_foo_table_spec(status_to_cb=None):
    return airtable.TableSpec(
        name="foo",
        model_cls=FooModel,
        status_to_cb=status_to_cb if status_to_cb is not None else dict(),
    )


#########
# TESTS #
#########


def test_snapshot_basic():
    test_model = FooModel(
        id=get_random_airtable_id(),
        created_at=get_random_created_at(),
        status="New",
    )

    # Getting modified fields before a snapshot should fail
    with pytest.raises(RuntimeError):
        test_model.get_modified_fields()

    test_model.snapshot()
    assert test_model.get_modified_fields() == set()

    test_model.name = "bar"

    assert test_model.get_modified_fields() == {"name"}
    assert test_model.to_airtable(modified_only=True)["fields"].keys() == {
        "name"
    }

    test_model.snapshot()
    assert test_model.get_modified_fields() == set()


def test_poll_table_basic():
    # TODO: refactor AirtableClient logic more and get rid of the mocks
    with mock.patch(
        f"{airtable.__name__}.AirtableClient.get_all_with_new_status"
    ) as mock_get, mock.patch(
        f"{airtable.__name__}.AirtableClient.update"
    ) as mock_update:
        # Test data
        test_model = FooModel(
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

        test_spec = get_foo_table_spec(
            {
                "New": lambda conf: on_new,
                "Processed": lambda conf: on_processed,
            }
        )

        # Mocks
        def mock_poll():
            if test_model.status != test_model.meta_last_seen_status:
                return [test_model]
            else:
                return []

        mock_get.side_effect = mock_poll
        client = test_spec.get_airtable_client(TEST_CONFIG.airtable)
        # Test
        poll_res = client.poll_table(TEST_CONFIG)

        assert poll_res
        assert test_model.status == "Processed"
        assert test_model.meta_last_seen_status == "New"
        assert mock_update.call_count == 1

        poll_res = client.poll_table(TEST_CONFIG)

        assert poll_res
        assert test_model.status == "Processed"
        assert test_model.meta_last_seen_status == "Processed"
        assert mock_update.call_count == 2

        # NOTE that this call should be a no-op
        poll_res = client.poll_table(TEST_CONFIG)

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

        test_spec = get_foo_table_spec({"New": lambda conf: on_new_mock})

        client = test_spec.get_airtable_client(TEST_CONFIG.airtable)
        poll_res = client.poll_table(TEST_CONFIG, max_num_retries=3)

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

        test_spec = get_foo_table_spec({"New": lambda conf: on_new_mock})
        client = test_spec.get_airtable_client(TEST_CONFIG.airtable)
        poll_res = client.poll_table(TEST_CONFIG, max_num_retries=3)

        assert poll_res
        assert test_model.status == "New"
        assert test_model.meta_last_seen_status == "New"
        assert mock_update.call_count == 1
        assert on_new_mock.call_count == 3
