import json

import pytest
from nucypher.utilities.concurrency import WorkerPool

from porter.fields.exceptions import InvalidInputData
from porter.schema import BucketSampling
from tests.constants import TEMPORARY_DOMAIN


@pytest.fixture(autouse=True)
def mock_bucket_request(mocker, ursulas):
    class MockRequestResponse:
        status_code = 200

        def json(self):
            buckets = {
                "bucket_A": [u.checksum_address for u in ursulas[: len(ursulas) // 2]],
                "bucket_B": [u.checksum_address for u in ursulas[len(ursulas) // 2 :]],
            }
            return buckets

    mocker.patch("requests.get", return_value=MockRequestResponse())


def test_bucket_sampling_schema(get_random_checksum_address):
    #
    # Input i.e. load
    #

    # no args
    with pytest.raises(InvalidInputData):
        BucketSampling().load({})

    quantity = 10
    required_data = {
        "quantity": quantity,
    }

    # required args
    BucketSampling().load(required_data)

    # missing required args
    updated_data = {k: v for k, v in required_data.items() if k != "quantity"}
    with pytest.raises(InvalidInputData):
        BucketSampling().load(updated_data)

    # optional components

    # only exclude
    updated_data = dict(required_data)
    exclude_ursulas = []
    for i in range(2):
        exclude_ursulas.append(get_random_checksum_address())
    updated_data["exclude_ursulas"] = exclude_ursulas
    BucketSampling().load(updated_data)

    # only random seed
    updated_data = dict(required_data)
    updated_data["random_seed"] = 42
    BucketSampling().load(updated_data)

    updated_data = dict(required_data)
    updated_data["random_seed"] = "42"
    BucketSampling().load(updated_data)

    # both exclude and timeout
    updated_data = dict(required_data)
    updated_data["exclude_ursulas"] = exclude_ursulas
    updated_data["timeout"] = 20
    BucketSampling().load(updated_data)

    # list input formatted as ',' separated strings
    updated_data = dict(required_data)
    updated_data["exclude_ursulas"] = ",".join(exclude_ursulas)
    data = BucketSampling().load(updated_data)
    assert data["exclude_ursulas"] == exclude_ursulas

    # single value as string cast to list
    updated_data = dict(required_data)
    updated_data["exclude_ursulas"] = exclude_ursulas[0]
    data = BucketSampling().load(updated_data)
    assert data["exclude_ursulas"] == [exclude_ursulas[0]]

    # invalid exclude entry
    updated_data = dict(required_data)
    updated_data["exclude_ursulas"] = list(exclude_ursulas)  # make copy to modify
    updated_data["exclude_ursulas"].append("0xdeadbeef")
    with pytest.raises(InvalidInputData):
        BucketSampling().load(updated_data)

    # invalid timeout value
    with pytest.raises(InvalidInputData):
        updated_data = dict(required_data)
        updated_data["timeout"] = "some number"
        BucketSampling().load(updated_data)

    with pytest.raises(InvalidInputData):
        updated_data = dict(required_data)
        updated_data["timeout"] = 0
        BucketSampling().load(updated_data)

    with pytest.raises(InvalidInputData):
        updated_data = dict(required_data)
        updated_data["timeout"] = -1
        BucketSampling().load(updated_data)

    # invalid random seed
    with pytest.raises(InvalidInputData):
        updated_data = dict(required_data)
        updated_data["random_seed"] = "a string"
        BucketSampling().load(updated_data)

    #
    # Output i.e. dump
    #
    ursulas = []
    expected_ursulas = []
    for i in range(10):
        ursula = get_random_checksum_address()
        ursulas.append(ursula.lower())

        expected_ursulas.append(ursula)

    output = BucketSampling().dump(obj={"ursulas": ursulas, "block_number": "42"})
    assert output == {"ursulas": expected_ursulas, "block_number": 42}


def test_bucket_sampling_python_interface(porter, ursulas, testerchain):

    porter._ALLOWED_DOMAINS_FOR_BUCKET_SAMPLING = (TEMPORARY_DOMAIN,)

    # simple
    quantity = 4
    sampled_ursulas, _block = porter.bucket_sampling(quantity=quantity)
    assert len(set(sampled_ursulas)) == quantity  # ensure no repeats

    ursulas_list = list(ursulas)

    # exclude specific ursulas
    exclude_ursulas = [ursulas_list[0]]
    sampled_ursulas, _block = porter.bucket_sampling(
        quantity=quantity, exclude_ursulas=exclude_ursulas
    )
    assert len(set(sampled_ursulas)) == quantity
    for address in exclude_ursulas:
        assert address not in sampled_ursulas

    # too many ursulas requested
    with pytest.raises(ValueError, match="Insufficient nodes"):
        porter.bucket_sampling(quantity=len(ursulas) + 1)

    # random seeds work as expected
    first_seed = 42
    sampled_ursulas_for_first_seed, _block = porter.bucket_sampling(
        quantity=quantity, random_seed=first_seed
    )

    second_seed = 1234
    sampled_ursulas_for_second_seed, _block = porter.bucket_sampling(
        quantity=quantity, random_seed=second_seed
    )
    resampled_ursulas_for_first_seed, _block = porter.bucket_sampling(
        quantity=quantity, random_seed=first_seed
    )

    assert sampled_ursulas_for_first_seed == resampled_ursulas_for_first_seed
    assert sampled_ursulas_for_second_seed != sampled_ursulas_for_first_seed

    # Bucket sampling caps works as expected:

    # If all population is partitioned to 2 buckets, sampling should only work up to 4 ursulas
    for _ in [0, 1, 2, 3, 4]:
        _, _ = porter.bucket_sampling(quantity=4)

    # When trying to sample more, it should fail since all bucket caps are reached.
    with pytest.raises(WorkerPool.OutOfValues):
        _, _ = porter.bucket_sampling(quantity=5)


@pytest.mark.parametrize("timeout", [None, 10])
@pytest.mark.parametrize("random_seed", [None, 42])
def test_bucket_sampling_web_interface(
    porter_web_controller, ursulas, timeout, random_seed
):

    # Send bad data to assert error return
    response = porter_web_controller.get(
        "/bucket_sampling", data=json.dumps({"bad": "input"})
    )
    assert response.status_code == 400

    quantity = 4
    ursulas_list = list(ursulas)
    exclude_ursulas = [
        ursulas_list[2].checksum_address,
        ursulas_list[3].checksum_address,
    ]

    get_ursulas_params = {
        "quantity": quantity,
        "exclude_ursulas": exclude_ursulas,
    }

    if timeout:
        get_ursulas_params["timeout"] = timeout

    if random_seed:
        get_ursulas_params["random_seed"] = random_seed

    #
    # Success
    #
    response = porter_web_controller.get(
        "/bucket_sampling", data=json.dumps(get_ursulas_params)
    )
    assert response.status_code == 200

    response_data = json.loads(response.data)
    sampled_ursulas = response_data["result"]["ursulas"]
    assert len(set(sampled_ursulas)) == quantity
    for address in exclude_ursulas:
        assert address not in sampled_ursulas

    #
    # Test Query parameters
    #
    query_params = (
        f"/bucket_sampling?quantity={quantity}"
        f'&exclude_ursulas={",".join(exclude_ursulas)}'
    )

    if timeout:
        query_params += f"&timeout={timeout}"

    if random_seed:
        query_params += f"&random_seed={random_seed}"

    response = porter_web_controller.get(
        "/bucket_sampling", data=json.dumps(get_ursulas_params)
    )
    assert response.status_code == 200

    response_data = json.loads(response.data)
    sampled_ursulas = response_data["result"]["ursulas"]
    assert len(set(sampled_ursulas)) == quantity
    for address in exclude_ursulas:
        assert address not in sampled_ursulas

    #
    # Failure case: too many ursulas requested
    #
    failed_ursula_params = dict(get_ursulas_params)
    failed_ursula_params["quantity"] = len(ursulas_list) + 1  # too many to get
    response = porter_web_controller.get(
        "/bucket_sampling", data=json.dumps(failed_ursula_params)
    )
    assert response.status_code == 400
    assert "Insufficient nodes" in response.text
