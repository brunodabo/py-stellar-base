from typing import List
import base64
from typing import List, Union
from xdrlib import Packer, Unpacker

from .exceptions import SignatureExistError
from .keypair import Keypair
from .network import Network
from .base_transaction_envelope import BaseTransactionEnvelope
from .transaction import Transaction
from .utils import sha256, hex_to_bytes
from .xdr import xdr as stellarxdr

__all__ = ["TransactionEnvelope"]


class TransactionEnvelope(BaseTransactionEnvelope["TransactionEnvelope"]):
    """The :class:`TransactionEnvelope` object, which represents a transaction
    envelope ready to sign and submit to send over the network.

    When a transaction is ready to be prepared for sending over the network, it
    must be put into a :class:`TransactionEnvelope`, which includes additional
    metadata such as the signers for a given transaction. Ultimately, this
    class handles signing and conversion to and from XDR for usage on Stellar's
    network.

    :param transaction: The transaction that is encapsulated in this envelope.
    :param list signatures: which contains a list of signatures that have
          already been created.
    :param network_passphrase: The network to connect to for verifying and retrieving additional attributes from.
    """

    def __init__(
        self,
        transaction: Transaction,
        network_passphrase: str,
        signatures: List[stellarxdr.DecoratedSignature] = None,
    ) -> None:
        super().__init__(network_passphrase, signatures)
        self.transaction = transaction

    def signature_base(self) -> bytes:
        """Get the signature base of this transaction envelope.

        Return the "signature base" of this transaction, which is the value
        that, when hashed, should be signed to create a signature that
        validators on the Stellar Network will accept.

        It is composed of a 4 prefix bytes followed by the xdr-encoded form of
        this transaction.

        :return: The signature base of this transaction envelope.

        """
        network_id = self.network_id
        tx_type = Xdr.StellarXDRPacker()
        tx_packer = Xdr.StellarXDRPacker()
        tx = self.transaction
        if isinstance(self.transaction, Transaction) and not self.transaction.v1:
            tx = Transaction.from_xdr_object(self.transaction.to_xdr_object(), v1=False)
            tx.v1 = True
        tx_type.pack_EnvelopeType(Xdr.const.ENVELOPE_TYPE_TX)
        tx_packer.pack_Transaction(tx.to_xdr_object())
        tx_type_buffer = tx_type.get_buffer()
        tx_buffer = tx_packer.get_buffer()
        return network_id + tx_type_buffer + tx_buffer

    def to_xdr_object(self) -> stellarxdr.TransactionEnvelope:
        """Get an XDR object representation of this :class:`TransactionEnvelope`.

        :return: XDR TransactionEnvelope object
        """
        tx = self.transaction.to_xdr_object()
        if self.transaction.v1:
            te_type = Xdr.const.ENVELOPE_TYPE_TX
            tx_envelope = Xdr.types.TransactionV1Envelope(tx, self.signatures)
            return Xdr.types.TransactionEnvelope(type=te_type, v1=tx_envelope)
        else:
            te_type = Xdr.const.ENVELOPE_TYPE_TX_V0
            tx_envelope = Xdr.types.TransactionV0Envelope(tx, self.signatures)
            return Xdr.types.TransactionEnvelope(type=te_type, v0=tx_envelope)

    def to_xdr(self) -> str:
        """Get the base64 encoded XDR string representing this
        :class:`TransactionEnvelope`.

        :return: XDR :class:`TransactionEnvelope` base64 string object
        """
        return self.to_xdr_object().to_xdr()

    @classmethod
    def from_xdr_object(
        cls, te_xdr_object: stellarxdr.TransactionEnvelope, network_passphrase: str
    ) -> "TransactionEnvelope":
        """Create a new :class:`TransactionEnvelope` from an XDR object.

        :param te_xdr_object: The XDR object that represents a transaction envelope.
        :param network_passphrase: The network to connect to for verifying and retrieving additional attributes from.

        :return: A new :class:`TransactionEnvelope` object from the given XDR TransactionEnvelope object.
        """
        te_type = te_xdr_object.type
        if te_type == Xdr.const.ENVELOPE_TYPE_TX_V0:
            tx = Transaction.from_xdr_object(te_xdr_object.v0, v1=False)
            signatures = te_xdr_object.v0.signatures
        elif te_type == Xdr.const.ENVELOPE_TYPE_TX:
            tx = Transaction.from_xdr_object(te_xdr_object.v1, v1=True)
            signatures = te_xdr_object.v1.signatures
        else:
            raise ValueError("Invalid EnvelopeType: %d.", te_xdr_object.type)
        te = cls(tx, network_passphrase=network_passphrase, signatures=signatures)
        return te

    @classmethod
    def from_xdr(cls, xdr: str, network_passphrase: str) -> "TransactionEnvelope":
        """Create a new :class:`TransactionEnvelope` from an XDR string.

        :param xdr: The XDR string that represents a transaction
            envelope.
        :param network_passphrase: The network to connect to for verifying and retrieving additional attributes from.

        :return: A new :class:`TransactionEnvelope` object from the given XDR TransactionEnvelope base64 string object.
        """
        data = base64.b64decode(xdr.encode())
        unpacker = Unpacker(data)
        xdr_obj = stellarxdr.TransactionEnvelope.unpack(unpacker)
        return cls.from_xdr_object(xdr_obj, network_passphrase)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented  # pragma: no cover
        return (
            self.transaction == other.transaction
            and self.network_id == other.network_id
            and self.signatures == other.signatures
        )

    def __str__(self):
        return (
            "<TransactionEnvelope [transaction={transaction}, network_id={network_id} "
            "signatures={signatures}]>".format(
                transaction=self.transaction,
                network_id=self.network_id,
                signatures=self.signatures,
            )
        )
