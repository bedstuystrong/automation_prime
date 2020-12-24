from unittest import mock

from ..utils import airtable

from .helpers import get_random_string, get_random_airtable_id

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


def test_poll_table_basic(mock_airtable_client):
    # Test data
    test_model = FooModel(
        id=get_random_airtable_id(),
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

    test_spec = get_foo_table_spec({"New": on_new, "Processed": on_processed})

    # Mocks
    def mock_poll(table_spec):
        assert table_spec.name == "foo"

        if test_model.status != test_model.meta_last_seen_status:
            return [test_model]
        else:
            return []

    mock_airtable_client.poll.side_effect = mock_poll

    # Test
    poll_res = airtable.poll_table(
        mock_airtable_client,
        test_spec,
    )

    assert poll_res
    assert test_model.status == "Processed"
    assert test_model.meta_last_seen_status == "New"
    assert mock_airtable_client.update.call_count == 1

    poll_res = airtable.poll_table(
        mock_airtable_client,
        test_spec,
    )

    assert poll_res
    assert test_model.status == "Processed"
    assert test_model.meta_last_seen_status == "Processed"
    assert mock_airtable_client.update.call_count == 2

    # NOTE that this call should be a no-op
    poll_res = airtable.poll_table(
        mock_airtable_client,
        test_spec,
    )

    assert poll_res
    assert mock_airtable_client.update.call_count == 2
    assert mock_airtable_client.poll.call_count == 3


def test_poll_table_retries(mock_airtable_client):
    test_model = FooModel(
        id=get_random_airtable_id(),
        status="New",
    )

    mock_airtable_client.poll.side_effect = lambda table_spec: [test_model]

    # NOTE that we have to create the mock from a no-op lambda to set magic
    # attributes used for logging in `poll_table`
    on_new_mock = mock.MagicMock(spec=lambda: None)

    test_spec = get_foo_table_spec({"New": on_new_mock})

    # Test case where all retries fail

    on_new_mock.side_effect = Exception("Fuuuuuu")

    poll_res = airtable.poll_table(
        mock_airtable_client,
        test_spec,
        max_num_retries=3,
    )

    assert not poll_res
    assert test_model.status == "New"
    assert test_model.meta_last_seen_status == "New"
    assert mock_airtable_client.update.call_count == 1
    assert on_new_mock.call_count == 3


def test_poll_table_retries_transient(mock_airtable_client):
    test_model = FooModel(
        id=get_random_airtable_id(),
        status="New",
    )

    mock_airtable_client.poll.side_effect = lambda table_spec: [test_model]

    # NOTE that we have to create the mock from a no-op lambda to set magic
    # attributes used for logging in `poll_table`
    on_new_mock = mock.MagicMock(spec=lambda: None)

    test_spec = get_foo_table_spec({"New": on_new_mock})
    on_new_mock.side_effect = [
        Exception("Fuuuuuu"),
        Exception("Fuuuuuu"),
        None,
    ]

    poll_res = airtable.poll_table(
        mock_airtable_client,
        test_spec,
        max_num_retries=3,
    )

    assert poll_res
    assert test_model.status == "New"
    assert test_model.meta_last_seen_status == "New"
    assert mock_airtable_client.update.call_count == 1
    assert on_new_mock.call_count == 3
