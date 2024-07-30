import base64
import random

import pytest
from nucypher.crypto.powers import DecryptingPower
from nucypher.policy.conditions.context import USER_ADDRESS_CONTEXT
from nucypher_core import TreasureMap as TreasureMapClass
from nucypher_core.umbral import PublicKey

from porter.fields.exceptions import (
    InvalidInputData,
    SpecificationError,
)
from porter.fields.treasuremap import TreasureMap
from porter.fields.umbralkey import UmbralKey
from porter.main import Porter
from porter.schema import (
    BaseSchema,
    PRERetrievalOutcomeSchema,
    PRERetrieveCFrags,
)
from porter.utils import retrieval_request_setup


def test_alice_revoke():
    pass  # TODO


def test_bob_retrieve_cfrags(
    porter,
    enacted_policy,
    bob,
    alice,
    valid_eip4361_auth_message,
    get_random_checksum_address,
):
    bob_retrieve_cfrags_schema = PRERetrieveCFrags()

    # no args
    with pytest.raises(InvalidInputData):
        bob_retrieve_cfrags_schema.load({})

    # Setup - no context
    retrieval_args, _ = retrieval_request_setup(
        enacted_policy, bob, alice, encode_for_rest=True
    )
    bob_retrieve_cfrags_schema.load(retrieval_args)

    context = {USER_ADDRESS_CONTEXT: valid_eip4361_auth_message}

    # simple schema load w/ optional context
    retrieval_args, _ = retrieval_request_setup(
        enacted_policy,
        bob,
        alice,
        encode_for_rest=True,
        context=context,
    )
    bob_retrieve_cfrags_schema.load(retrieval_args)

    # invalid context specified
    retrieval_args, _ = retrieval_request_setup(
        enacted_policy,
        bob,
        alice,
        encode_for_rest=True,
        context=[1, 2, 3],  # list instead of dict
    )
    with pytest.raises(InvalidInputData):
        # invalid context type
        bob_retrieve_cfrags_schema.load(retrieval_args)

    # missing required argument
    updated_data = dict(retrieval_args)
    updated_data.pop("context")  # context is not a required param
    key_to_remove = random.choice(list(updated_data.keys()))
    del updated_data[key_to_remove]
    with pytest.raises(InvalidInputData):
        # missing arg
        bob_retrieve_cfrags_schema.load(updated_data)

    #
    # Retrieval output for 1 retrieval kit
    #
    non_encoded_retrieval_args, _ = retrieval_request_setup(
        enacted_policy,
        bob,
        alice,
        encode_for_rest=False,
        context=context,
    )
    retrieval_outcomes = porter.retrieve_cfrags(**non_encoded_retrieval_args)
    expected_retrieval_results_json = []
    retrieval_outcome_schema = PRERetrievalOutcomeSchema()

    assert len(retrieval_outcomes) == 1
    assert len(retrieval_outcomes[0].cfrags) > 0
    assert len(retrieval_outcomes[0].errors) == 0
    for outcome in retrieval_outcomes:
        data = retrieval_outcome_schema.dump(outcome)
        expected_retrieval_results_json.append(data)

    output = bob_retrieve_cfrags_schema.dump(
        obj={"retrieval_results": retrieval_outcomes}
    )
    assert output == {"retrieval_results": expected_retrieval_results_json}
    assert len(output["retrieval_results"]) == 1
    assert len(output["retrieval_results"][0]["cfrags"]) > 0
    assert len(output["retrieval_results"][0]["errors"]) == 0

    # now include errors
    errors = {
        get_random_checksum_address(): "Error Message 1",
        get_random_checksum_address(): "Error Message 2",
        get_random_checksum_address(): "Error Message 3",
    }
    new_retrieval_outcome = Porter.PRERetrievalOutcome(
        cfrags=retrieval_outcomes[0].cfrags, errors=errors
    )
    expected_retrieval_results_json = [
        retrieval_outcome_schema.dump(new_retrieval_outcome)
    ]
    output = bob_retrieve_cfrags_schema.dump(
        obj={"retrieval_results": [new_retrieval_outcome]}
    )
    assert output == {"retrieval_results": expected_retrieval_results_json}
    assert len(output["retrieval_results"]) == 1
    assert len(output["retrieval_results"][0]["cfrags"]) > 0
    assert len(output["retrieval_results"][0]["errors"]) == len(errors)

    #
    # Retrieval output for multiple retrieval kits
    #
    num_retrieval_kits = 4
    non_encoded_retrieval_args, _ = retrieval_request_setup(
        enacted_policy,
        bob,
        alice,
        encode_for_rest=False,
        context=context,
        num_random_messages=num_retrieval_kits,
    )
    retrieval_outcomes = porter.retrieve_cfrags(**non_encoded_retrieval_args)
    expected_retrieval_results_json = []
    retrieval_outcome_schema = PRERetrievalOutcomeSchema()

    assert len(retrieval_outcomes) == num_retrieval_kits
    for i in range(num_retrieval_kits):
        assert len(retrieval_outcomes[i].cfrags) > 0
        assert len(retrieval_outcomes[i].errors) == 0
    for outcome in retrieval_outcomes:
        data = retrieval_outcome_schema.dump(outcome)
        expected_retrieval_results_json.append(data)

    output = bob_retrieve_cfrags_schema.dump(
        obj={"retrieval_results": retrieval_outcomes}
    )
    assert output == {"retrieval_results": expected_retrieval_results_json}

    # now include errors
    error_message_template = "Retrieval Kit {} - Error Message {}"
    new_retrieval_outcomes_with_errors = []
    for i in range(num_retrieval_kits):
        specific_kit_errors = dict()
        for j in range(i):
            # different number of errors for each kit; 1 error for kit 1, 2 errors for kit 2 etc.
            specific_kit_errors[get_random_checksum_address()] = (
                error_message_template.format(i, j)
            )
        new_retrieval_outcomes_with_errors.append(
            Porter.PRERetrievalOutcome(
                cfrags=retrieval_outcomes[i].cfrags, errors=specific_kit_errors
            )
        )

    expected_retrieval_results_json = []
    for outcome in new_retrieval_outcomes_with_errors:
        data = retrieval_outcome_schema.dump(outcome)
        expected_retrieval_results_json.append(data)

    output = bob_retrieve_cfrags_schema.dump(
        obj={"retrieval_results": new_retrieval_outcomes_with_errors}
    )
    assert output == {"retrieval_results": expected_retrieval_results_json}
    assert len(output["retrieval_results"]) == num_retrieval_kits
    for i in range(num_retrieval_kits):
        assert len(output["retrieval_results"][i]["cfrags"]) > 0
        # ensures errors are associated appropriately
        kit_errors = output["retrieval_results"][i]["errors"]
        assert len(kit_errors) == i
        values = kit_errors.values()  # ordered?
        for j in range(i):
            assert error_message_template.format(i, j) in values


def make_header(brand: bytes, major: int, minor: int) -> bytes:
    # Hardcoding this since it's too much trouble to expose it all the way from Rust
    assert len(brand) == 4
    major_bytes = major.to_bytes(2, "big")
    minor_bytes = minor.to_bytes(2, "big")
    header = brand + major_bytes + minor_bytes
    return header


def test_treasure_map_validation(enacted_policy, bob):
    class UnenncryptedTreasureMapsOnly(BaseSchema):
        tmap = TreasureMap()

    # this will raise a base64 error
    with pytest.raises(SpecificationError) as e:
        UnenncryptedTreasureMapsOnly().load(
            {"tmap": "your face looks like a treasure map"}
        )

    # assert that field name is in the error message
    assert "Could not parse tmap" in str(e)
    assert "Invalid base64-encoded string" in str(e)

    # valid base64 but invalid treasuremap
    bad_map = make_header(b"TMap", 1, 0) + b"your face looks like a treasure map"
    bad_map_b64 = base64.b64encode(bad_map).decode()

    with pytest.raises(InvalidInputData) as e:
        UnenncryptedTreasureMapsOnly().load({"tmap": bad_map_b64})

    assert "Could not convert input for tmap to a TreasureMap" in str(e)
    assert "Failed to deserialize" in str(e)

    # a valid treasuremap
    decrypted_treasure_map = bob._decrypt_treasure_map(
        enacted_policy.treasure_map, enacted_policy.publisher_verifying_key
    )
    tmap_bytes = bytes(decrypted_treasure_map)
    tmap_b64 = base64.b64encode(tmap_bytes).decode()
    result = UnenncryptedTreasureMapsOnly().load({"tmap": tmap_b64})
    assert isinstance(result["tmap"], TreasureMapClass)


def test_key_validation(bob):
    class BobKeyInputRequirer(BaseSchema):
        bobkey = UmbralKey()

    with pytest.raises(InvalidInputData) as e:
        BobKeyInputRequirer().load({"bobkey": "I am the key to nothing"})
    assert "non-hexadecimal number found in fromhex()" in str(e)
    assert "bobkey" in str(e)

    with pytest.raises(InvalidInputData) as e:
        BobKeyInputRequirer().load({"bobkey": "I am the key to nothing"})
    assert "non-hexadecimal number found in fromhex()" in str(e)
    assert "bobkey" in str(e)

    with pytest.raises(InvalidInputData) as e:
        # lets just take a couple bytes off (less bytes than required)
        BobKeyInputRequirer().load(
            {
                "bobkey": (
                    "02f0cb3f3a33f16255d9b2586e6c56570aa07bbeb1157e169f1fb114ffb40037"
                )
            }
        )
    assert "Could not convert input for bobkey to an Umbral Key" in str(e)

    result = BobKeyInputRequirer().load(
        dict(bobkey=bob.public_keys(DecryptingPower).to_compressed_bytes().hex())
    )
    assert isinstance(result["bobkey"], PublicKey)
