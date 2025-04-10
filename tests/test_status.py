import json
from collections import defaultdict

from porter.interfaces import UrsulaStatusData
from porter.schema import Status, UrsulaStatusDataSchema


def test_get_ursulas_schema(get_random_checksum_address):
    #
    # Output i.e. dump
    #
    overall_status_data = defaultdict(list)
    expected_ursulas_status_data = defaultdict(list)
    for i in range(5):
        ursula_status_data = UrsulaStatusData(
            nickname=f"Name Name Name Name {i}",
            staker_address=get_random_checksum_address(),
            operator_address=get_random_checksum_address(),
            rest_url="https://node.com:9151/status",
        )
        key = "unverified"
        if i % 2 == 0:
            key = "verified"

        overall_status_data[key].append(ursula_status_data)
        # use schema to determine expected output (encrypting key gets changed to hex)
        expected_ursulas_status_data[key].append(
            UrsulaStatusDataSchema().dump(ursula_status_data)
        )

    output = Status().dump(obj={"known_nodes": overall_status_data})
    assert output == {"known_nodes": expected_ursulas_status_data}


def test_status_web_interface(
    porter,
    ursulas,
    porter_web_controller,
    excluded_staker_address_for_duration_greater_than_0,
):
    # Send bad data to assert error return
    response = porter_web_controller.get("/status", data=json.dumps({"bad": "input"}))
    assert response.status_code == 400

    #
    # Success
    #
    response = porter_web_controller.get("/status")
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "known_nodes" in response_data["result"]
    known_nodes = response_data["result"]["known_nodes"]
    assert len(known_nodes["verified"]) == len(ursulas)

    ursulas_dict = {
        ursula.checksum_address: ursula.status_info(omit_known_nodes=True)
        for ursula in ursulas
    }
    for ursula_status_data in known_nodes["verified"]:
        ursula_status_info = ursulas_dict[ursula_status_data["staker_address"]]
        assert ursula_status_info.staker_address == ursula_status_data["staker_address"]
        # assert ursula_status_info.operator_address == ursula_status_data.get("operator_address")
        assert str(ursula_status_info.nickname) == ursula_status_data["nickname"]
        assert (
            f"https://{ursula_status_info.rest_url}/status"
            == ursula_status_data["rest_url"]
        )
