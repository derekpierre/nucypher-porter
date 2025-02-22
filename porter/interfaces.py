from typing import Dict, List, Optional

from eth_typing import ChecksumAddress
from nucypher_core import RetrievalKit, TreasureMap
from nucypher_core.umbral import PublicKey

from nucypher.control.interfaces import ControlInterface, attach_schema
from porter import schema


class PorterInterface(ControlInterface):
    def __init__(self, porter: 'Porter' = None, *args, **kwargs):
        super().__init__(implementer=porter, *args, **kwargs)

    #
    # Alice Endpoints
    #
    @attach_schema(schema.AliceGetUrsulas)
    def get_ursulas(self,
                    quantity: int,
                    exclude_ursulas: Optional[List[ChecksumAddress]] = None,
                    include_ursulas: Optional[List[ChecksumAddress]] = None) -> Dict:
        ursulas_info = self.implementer.get_ursulas(
            quantity=quantity,
            exclude_ursulas=exclude_ursulas,
            include_ursulas=include_ursulas,
        )

        response_data = {"ursulas": ursulas_info}  # list of UrsulaInfo objects
        return response_data

    @attach_schema(schema.AliceRevoke)
    def revoke(self) -> dict:
        # Steps (analogous to nucypher.character.control.interfaces):
        # 1. creation of objects / setup
        # 2. call self.implementer.some_function() i.e. Porter learner has an associated function to call
        # 3. create response
        pass

    @attach_schema(schema.BobRetrieveCFrags)
    def retrieve_cfrags(self,
                        treasure_map: TreasureMap,
                        retrieval_kits: List[RetrievalKit],
                        alice_verifying_key: PublicKey,
                        bob_encrypting_key: PublicKey,
                        bob_verifying_key: PublicKey,
                        context: Optional[Dict] = None) -> Dict:
        retrieval_outcomes = self.implementer.retrieve_cfrags(
            treasure_map=treasure_map,
            retrieval_kits=retrieval_kits,
            alice_verifying_key=alice_verifying_key,
            bob_encrypting_key=bob_encrypting_key,
            bob_verifying_key=bob_verifying_key,
            context=context,
        )
        response_data = {
            "retrieval_results": retrieval_outcomes
        }  # list of RetrievalOutcome objects
        return response_data
