from typing import List, Union

from .keypair import Keypair
from .memo import NoneMemo, Memo
from .muxed_account import MuxedAccount
from .operation.operation import Operation
from .strkey import StrKey
from .time_bounds import TimeBounds
from .xdr import xdr as stellarxdr

__all__ = ["Transaction"]


class Transaction:
    """The :class:`Transaction` object, which represents a transaction(Transaction or TransactionV0)
    on Stellar's network.

    A transaction contains a list of operations, which are all executed
    in order as one ACID transaction, along with an
    associated source account, fee, account sequence number, list of
    signatures, both an optional memo and an optional TimeBounds. Typically a
    :class:`Transaction` is placed in a :class:`TransactionEnvelope
    <stellar_sdk.transaction_envelope.TransactionEnvelope>` which is
    then signed before being sent over the network.

    For more information on Transactions in Stellar, see `Stellar's guide
    on transactions`_.

    .. _Stellar's guide on transactions:
        https://www.stellar.org/developers/guides/concepts/transactions.html

    :param source: the source account for the transaction.
    :param sequence: The sequence number for the transaction.
    :param fee: The fee amount for the transaction, which should equal
          FEE (currently 100 stroops) multiplied by the number of
          operations in the transaction. See `Stellar's latest documentation
          on fees
          <https://www.stellar.org/developers/guides/concepts/fees.html#transaction-fee>`_
          for more information.
    :param operations: A list of operations objects (typically its
          subclasses as defined in :mod:`stellar_sdk.operation.Operation`.
    :param time_bounds: The timebounds for the validity of this transaction.
    :param memo: The memo being sent with the transaction, being
          represented as one of the subclasses of the
          :class:`Memo <stellar_sdk.memo.Memo>` object.
    :param v1: Temporary feature flag to allow alpha testing of Stellar Protocol 13 transactions.
        We will remove this once all transactions are supposed to be v1.
        See `CAP-0015 <https://github.com/stellar/stellar-protocol/blob/master/core/cap-0015.md>`_ for more information.
    """

    def __init__(
        self,
        source: Union[Keypair, MuxedAccount, str],
        sequence: int,
        fee: int,
        operations: List[Operation],
        memo: Memo = None,
        time_bounds: TimeBounds = None,
        v1: bool = False,
    ) -> None:

        # if not operations:
        #     raise ValueError("At least one operation required.")

        if memo is None:
            memo = NoneMemo()
        if isinstance(source, Keypair):
            source = MuxedAccount(account_id=source.public_key, account_id_id=None)
        if isinstance(source, str):
            source = MuxedAccount.from_account(source)

        self.source: [MuxedAccount, str] = source
        self.sequence: int = sequence
        self.operations: List[Operation] = operations
        self.memo: Memo = memo
        self.fee: int = fee
        self.time_bounds: TimeBounds = time_bounds
        self.v1: bool = v1

    def to_xdr_object(self) -> stellarxdr.Transaction:
        """Get an XDR object representation of this :class:`Transaction`.

        :return: XDR Transaction object
        """
        memo = self.memo.to_xdr_object()
        operations = [operation.to_xdr_object() for operation in self.operations]
        time_bounds = (
            self.time_bounds.to_xdr_object() if self.time_bounds is not None else None
        )
        ext = stellarxdr.TransactionExt(0)
        if self.v1:
            return stellarxdr.Transaction(
                source_account,
                stellarxdr.Uint32(self.fee),
                stellarxdr.SequenceNumber(stellarxdr.Int64(self.sequence)),
                time_bounds,
                memo,
                operations,
                ext,
            )
        source_xdr = (
            Keypair.from_public_key(self.source.account_id).xdr_account_id().ed25519
        )
        return Xdr.types.TransactionV0(
            source_xdr, self.fee, self.sequence, time_bounds, memo, operations, ext,
        )

    @classmethod
    def from_xdr_object(
        cls,
        tx_xdr_object: Union[Xdr.types.Transaction, Xdr.types.TransactionV0],
        v1: bool = False,
    ) -> "Transaction":
        """Create a new :class:`Transaction` from an XDR object.

        :param tx_xdr_object: The XDR object that represents a transaction.
        :param v1: Temporary feature flag to allow alpha testing of Stellar Protocol 13 transactions.
            We will remove this once all transactions are supposed to be v1.
            See `CAP-0015 <https://github.com/stellar/stellar-protocol/blob/master/core/cap-0015.md>`_
            for more information.

        :return: A new :class:`Transaction` object from the given XDR Transaction object.
        """
        if v1:
            source = MuxedAccount.from_xdr_object(tx_xdr_object.sourceAccount)
        else:
            source = StrKey.encode_ed25519_public_key(
                tx_xdr_object.sourceAccountEd25519
            )
        # TODO
        source = Keypair.from_public_key(
            StrKey.encode_ed25519_public_key(
                tx_xdr_object.source_account.account_id.ed25519.uint256
            )
        )
        sequence = tx_xdr_object.seq_num.sequence_number.int64
        fee = tx_xdr_object.fee.uint32
        time_bounds_xdr = tx_xdr_object.time_bounds
        time_bounds = (
            None
            if time_bounds_xdr is None
            else TimeBounds.from_xdr_object(time_bounds_xdr)
        )
        memo = Memo.from_xdr_object(tx_xdr_object.memo)
        operations = list(map(Operation.from_xdr_object, tx_xdr_object.operations))
        return cls(
            source=source,
            sequence=sequence,
            time_bounds=time_bounds,
            memo=memo,
            fee=fee,
            operations=operations,
            v1=v1,
        )

    def to_xdr(self) -> str:
        """Get the base64 encoded XDR string representing this
        :class:`Transaction`.

        :return: XDR :class:`Transaction` base64 string object
        """
        return self.to_xdr_object().to_xdr()

    @classmethod
    def from_xdr(cls, xdr: str, v1: bool = False) -> "Transaction":
        """Create a new :class:`Transaction` from an XDR string.

        :param xdr: The XDR string that represents a :class:`Transaction`.
        :param v1: Temporary feature flag to allow alpha testing of Stellar Protocol 13 transactions.
            We will remove this once all transactions are supposed to be v1.
            See `CAP-0015 <https://github.com/stellar/stellar-protocol/blob/master/core/cap-0015.md>`_
            for more information.

        :return: A new :class:`Transaction` object from the given XDR Transaction base64 string object.
        """
        if v1:
            xdr_object = Xdr.types.Transaction.from_xdr(xdr)
        else:
            xdr_object = Xdr.types.TransactionV0.from_xdr(xdr)
        return cls.from_xdr_object(xdr_object, v1)
        xdr_obj = stellarxdr.Transaction.from_xdr(xdr)
        return cls.from_xdr_object(xdr_obj)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented  # pragma: no cover
        return (
            self.source == other.source
            and self.sequence == other.sequence
            and self.fee == other.fee
            and self.operations == other.operations
            and self.memo == other.memo
            and self.time_bounds == other.time_bounds
        )

    def __str__(self):
        return (
            "<Transaction [source={source}, sequence={sequence}, fee={fee}, "
            "operations={operations}, memo={memo}, time_bounds={time_bounds}]>".format(
                source=self.source,
                sequence=self.sequence,
                fee=self.fee,
                operations=self.operations,
                memo=self.memo,
                time_bounds=self.time_bounds,
            )
        )
