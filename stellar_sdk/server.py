from typing import Union, Coroutine, Any, Dict, List, Tuple, Generator

from stellar_sdk.base_transaction_envelope import BaseTransactionEnvelope
from .account import Account, Thresholds
from .asset import Asset
from .call_builder.accounts_call_builder import AccountsCallBuilder
from .call_builder.assets_call_builder import AssetsCallBuilder
from .call_builder.data_call_builder import DataCallBuilder
from .call_builder.effects_call_builder import EffectsCallBuilder
from .call_builder.fee_stats_call_builder import FeeStatsCallBuilder
from .call_builder.ledgers_call_builder import LedgersCallBuilder
from .call_builder.offers_call_builder import OffersCallBuilder
from .call_builder.operations_call_builder import OperationsCallBuilder
from .call_builder.orderbook_call_builder import OrderbookCallBuilder
from .call_builder.payments_call_builder import PaymentsCallBuilder
from .call_builder.root_call_builder import RootCallBuilder
from .call_builder.strict_receive_paths_call_builder import (
    StrictReceivePathsCallBuilder,
)
from .call_builder.strict_send_paths_call_builder import StrictSendPathsCallBuilder
from .call_builder.trades_aggregation_call_builder import TradeAggregationsCallBuilder
from .call_builder.trades_call_builder import TradesCallBuilder
from .call_builder.transactions_call_builder import TransactionsCallBuilder
from .client.base_async_client import BaseAsyncClient
from .client.base_sync_client import BaseSyncClient
from .client.requests_client import RequestsClient
from .exceptions import TypeError, NotFoundError, raise_request_exception
from .fee_bump_transaction import FeeBumpTransaction
from .fee_bump_transaction_envelope import FeeBumpTransactionEnvelope
from .helpers import parse_transaction_envelope_from_xdr
from .memo import NoneMemo
from .response.account_response import AccountResponse
from .response.asset_response import AssetResponse
from .response.data_response import DataResponse
from .response.effect_response import EFFECT_RESPONSE_TYPE_UNION
from .response.fee_stats_response import FeeStatsResponse
from .response.ledger_response import LedgerResponse
from .response.offer_response import OfferResponse
from .response.operation_response import (
    OPERATION_RESPONSE_TYPE_UNION,
    PAYMENT_RESPONSE_TYPE_UNION,
)
from .response.orderbook_response import OrderbookResponse
from .response.payment_path_response import PaymentPathResponse
from .response.trade_response import TradeResponse
from .response.trades_aggregation_response import TradesAggregationResponse
from .response.transaction_response import TransactionResponse
from .response.wrapped_response import WrappedResponse
from .muxed_account import MuxedAccount
from .sep.exceptions import AccountRequiresMemoError
from .transaction import Transaction
from .transaction_envelope import TransactionEnvelope
from .utils import (
    urljoin_with_query,
    MUXED_ACCOUNT_STARTING_LETTER,
)
from .xdr import Xdr
from .utils import urljoin_with_query
from .xdr.xdr import OperationType

__all__ = ["Server"]


class Server:
    """Server handles the network connection to a `Horizon <https://www.stellar.org/developers/horizon/reference/>`_
    instance and exposes an interface for requests to that instance.

    Here we need to talk about the **client** parameter, if you do not specify the client, we will use
    the :class:`stellar_sdk.client.requests_client.RequestsClient` instance by default, it is a synchronous HTTPClient,
    you can also specify an asynchronous HTTP Client,
    for example: :class:`stellar_sdk.client.aiohttp_client.AiohttpClient`. If you use a synchronous client,
    then all requests are synchronous. If you use an asynchronous client,
    then all requests are asynchronous. The choice is in your hands.

    :param horizon_url: Horizon Server URL (ex. `https://horizon-testnet.stellar.org`)
    :param client: Http Client used to send the request
    :raises: :exc:`TypeError <stellar_sdk.exceptions.TypeError>`: if the ``client`` does not meet the standard.
    """

    def __init__(
        self,
        horizon_url: str = "https://horizon-testnet.stellar.org/",
        client: Union[BaseAsyncClient, BaseSyncClient] = None,
    ) -> None:
        self.horizon_url: str = horizon_url

        if not client:
            client = RequestsClient()
        self._client: Union[BaseAsyncClient, BaseSyncClient] = client

        if isinstance(self._client, BaseAsyncClient):
            self.__async: bool = True
        elif isinstance(self._client, BaseSyncClient):
            self.__async = False
        else:
            raise TypeError(
                "This `client` class should be an instance "
                "of `stellar_sdk.client.base_async_client.BaseAsyncClient` "
                "or `stellar_sdk.client.base_sync_client.BaseSyncClient`."
            )

    def submit_transaction(
        self,
        transaction_envelope: Union[TransactionEnvelope, str],
        skip_memo_required_check: bool = False,
    ) -> Union[
        WrappedResponse[TransactionResponse],
        Coroutine[Any, Any, WrappedResponse[TransactionResponse]],
    ]:
        """Submits a transaction to the network.

        :param transaction_envelope: :class:`stellar_sdk.transaction_envelope.TransactionEnvelope` object
            or base64 encoded xdr
        :return: the response from horizon
        :raises:
            :exc:`ConnectionError <stellar_sdk.exceptions.ConnectionError>`
            :exc:`NotFoundError <stellar_sdk.exceptions.NotFoundError>`
            :exc:`BadRequestError <stellar_sdk.exceptions.BadRequestError>`
            :exc:`BadResponseError <stellar_sdk.exceptions.BadResponseError>`
            :exc:`UnknownRequestError <stellar_sdk.exceptions.UnknownRequestError>`
            :exc:`AccountRequiresMemoError <stellar_sdk.sep.exceptions.AccountRequiresMemoError>`
        """
        if self.__async:
            return self.__submit_transaction_async(
                transaction_envelope, skip_memo_required_check
            )
        return self.__submit_transaction_sync(
            transaction_envelope, skip_memo_required_check
        )

    def __submit_transaction_sync(
        self,
        transaction_envelope: Union[TransactionEnvelope, str],
        skip_memo_required_check: bool,
    ) -> WrappedResponse[TransactionResponse]:
        url = urljoin_with_query(self.horizon_url, "transactions")
        xdr, tx = self.__get_xdr_and_transaction_from_transaction_envelope(
            transaction_envelope
        )
        if not skip_memo_required_check:
            self.__check_memo_required_sync(tx)
        data = {"tx": xdr}
        resp = self._client.post(url=url, data=data)
        raise_request_exception(resp)
        return WrappedResponse(
            parse_func=self._parse_success_transaction, raw_response=resp
        )

    async def __submit_transaction_async(
        self,
        transaction_envelope: Union[TransactionEnvelope, str],
        skip_memo_required_check: bool,
    ) -> WrappedResponse[TransactionResponse]:
        url = urljoin_with_query(self.horizon_url, "transactions")
        xdr, tx = self.__get_xdr_and_transaction_from_transaction_envelope(
            transaction_envelope
        )
        if not skip_memo_required_check:
            await self.__check_memo_required_async(tx)
        data = {"tx": xdr}
        resp = await self._client.post(url=url, data=data)
        raise_request_exception(resp)
        return WrappedResponse(
            parse_func=self._parse_success_transaction, raw_response=resp
        )

    def __get_xdr_and_transaction_from_transaction_envelope(
        self,
        transaction_envelope: Union[
            TransactionEnvelope, FeeBumpTransactionEnvelope, str
        ],
    ) -> Tuple[str, Union[Transaction, FeeBumpTransaction]]:
        if isinstance(transaction_envelope, BaseTransactionEnvelope):
            xdr = transaction_envelope.to_xdr()
            tx = transaction_envelope.transaction
        else:
            xdr = transaction_envelope
            tx = parse_transaction_envelope_from_xdr(
                transaction_envelope, ""
            ).transaction
        return xdr, tx

    def _parse_success_transaction(self, raw_data: dict) -> TransactionResponse:
        return TransactionResponse.parse_obj(raw_data)

    def root(self) -> RootCallBuilder:
        """
        :return: New :class:`stellar_sdk.call_builder.RootCallBuilder` object configured
            by a current Horizon server configuration.
        """
        return RootCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def accounts(self) -> AccountsCallBuilder[List[AccountResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.AccountsCallBuilder` object configured
            by a current Horizon server configuration.
        """
        return AccountsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def assets(self) -> AssetsCallBuilder[List[AssetResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.AssetsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return AssetsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def data(self, account_id: str, data_name: str) -> DataCallBuilder[DataResponse]:
        """
        :return: New :class:`stellar_sdk.call_builder.DataCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return DataCallBuilder(
            horizon_url=self.horizon_url,
            client=self._client,
            account_id=account_id,
            data_name=data_name,
        )

    def effects(self) -> EffectsCallBuilder[List[EFFECT_RESPONSE_TYPE_UNION]]:
        """
        :return: New :class:`stellar_sdk.call_builder.EffectsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return EffectsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def fee_stats(self) -> FeeStatsCallBuilder[FeeStatsResponse]:
        """
        :return: New :class:`stellar_sdk.call_builder.FeeStatsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return FeeStatsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def ledgers(self) -> LedgersCallBuilder[List[LedgerResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.LedgersCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return LedgersCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def offers(self) -> OffersCallBuilder[List[OfferResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.OffersCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return OffersCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def operations(self) -> OperationsCallBuilder[List[OPERATION_RESPONSE_TYPE_UNION]]:
        """
        :return: New :class:`stellar_sdk.call_builder.OperationsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return OperationsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def orderbook(
        self, selling: Asset, buying: Asset
    ) -> OrderbookCallBuilder[OrderbookResponse]:
        """
        :param selling: Asset being sold
        :param buying: Asset being bought
        :return: New :class:`stellar_sdk.call_builder.OrderbookCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return OrderbookCallBuilder(
            horizon_url=self.horizon_url,
            client=self._client,
            buying=buying,
            selling=selling,
        )

    def strict_receive_paths(
        self,
        source: Union[str, List[Asset]],
        destination_asset: Asset,
        destination_amount: str,
    ) -> StrictReceivePathsCallBuilder[List[PaymentPathResponse]]:
        """
        :param source: The sender's account ID or a list of Assets. Any returned path must use a source that the sender can hold.
        :param destination_asset: The destination asset.
        :param destination_amount: The amount, denominated in the destination asset, that any returned path should be able to satisfy.
        :return: New :class:`stellar_sdk.call_builder.StrictReceivePathsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return StrictReceivePathsCallBuilder(
            horizon_url=self.horizon_url,
            client=self._client,
            source=source,
            destination_asset=destination_asset,
            destination_amount=destination_amount,
        )

    def strict_send_paths(
        self,
        source_asset: Asset,
        source_amount: str,
        destination: Union[str, List[Asset]],
    ) -> StrictSendPathsCallBuilder[List[PaymentPathResponse]]:
        """
        :param source_asset: The asset to be sent.
        :param source_amount: The amount, denominated in the source asset, that any returned path should be able to satisfy.
        :param destination: The destination account or the destination assets.
        :return: New :class:`stellar_sdk.call_builder.StrictReceivePathsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return StrictSendPathsCallBuilder(
            horizon_url=self.horizon_url,
            client=self._client,
            source_asset=source_asset,
            source_amount=source_amount,
            destination=destination,
        )

    def payments(self) -> PaymentsCallBuilder[List[PAYMENT_RESPONSE_TYPE_UNION]]:
        """
        :return: New :class:`stellar_sdk.call_builder.PaymentsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return PaymentsCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def trade_aggregations(
        self,
        base: Asset,
        counter: Asset,
        resolution: int,
        start_time: int = None,
        end_time: int = None,
        offset: int = None,
    ) -> TradeAggregationsCallBuilder[List[TradesAggregationResponse]]:
        """
        :param base: base asset
        :param counter: counter asset
        :param resolution: segment duration as millis since epoch. *Supported values
            are 1 minute (60000), 5 minutes (300000), 15 minutes (900000),
            1 hour (3600000), 1 day (86400000) and 1 week (604800000).*
        :param start_time: lower time boundary represented as millis since epoch
        :param end_time: upper time boundary represented as millis since epoch
        :param offset: segments can be offset using this parameter.
            Expressed in milliseconds. *Can only be used if the resolution is greater than 1 hour.
            Value must be in whole hours, less than the provided resolution, and less than 24 hours.*
        :return: New :class:`stellar_sdk.call_builder.TradeAggregationsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return TradeAggregationsCallBuilder(
            horizon_url=self.horizon_url,
            client=self._client,
            base=base,
            counter=counter,
            start_time=start_time,
            end_time=end_time,
            resolution=resolution,
            offset=offset,
        )

    def trades(self) -> TradesCallBuilder[List[TradeResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.TradesCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return TradesCallBuilder(horizon_url=self.horizon_url, client=self._client)

    def transactions(self) -> TransactionsCallBuilder[List[TransactionResponse]]:
        """
        :return: New :class:`stellar_sdk.call_builder.TransactionsCallBuilder` object configured by
            a current Horizon server configuration.
        """
        return TransactionsCallBuilder(
            horizon_url=self.horizon_url, client=self._client
        )

    def load_account(
        self, account_id: str
    ) -> Union[Account, Coroutine[Any, Any, Account]]:
        """Fetches an account's most current state in the ledger and then creates
        and returns an :class:`stellar_sdk.account.Account` object.

        :param account_id: The account to load.
        :return: an :class:`stellar_sdk.account.Account` object.
        :raises:
            :exc:`ConnectionError <stellar_sdk.exceptions.ConnectionError>`
            :exc:`NotFoundError <stellar_sdk.exceptions.NotFoundError>`
            :exc:`BadRequestError <stellar_sdk.exceptions.BadRequestError>`
            :exc:`BadResponseError <stellar_sdk.exceptions.BadResponseError>`
            :exc:`UnknownRequestError <stellar_sdk.exceptions.UnknownRequestError>`
        """
        if self.__async:
            return self.__load_account_async(account_id)
        return self.__load_account_sync(account_id)

    async def __load_account_async(self, account_id: str) -> Account:
        ed25519_account_id = MuxedAccount.from_account(account_id).account_id
        resp = await self.accounts().account_id(account_id=ed25519_account_id).call()
        sequence = int(resp.raw_data["sequence"])
        thresholds = Thresholds(
            resp.raw_data["thresholds"]["low_threshold"],
            resp.raw_data["thresholds"]["med_threshold"],
            resp.raw_data["thresholds"]["high_threshold"],
        )
        account = Account(account_id=account_id, sequence=sequence)
        account.signers = resp.raw_data["signers"]
        account.thresholds = thresholds
        return account

    def __load_account_sync(self, account_id: str) -> Account:
        ed25519_account_id = MuxedAccount.from_account(account_id).account_id
        resp = self.accounts().account_id(account_id=ed25519_account_id).call()
        sequence = int(resp.raw_data["sequence"])
        thresholds = Thresholds(
            resp.raw_data["thresholds"]["low_threshold"],
            resp.raw_data["thresholds"]["med_threshold"],
            resp.raw_data["thresholds"]["high_threshold"],
        )
        account = Account(account_id=account_id, sequence=sequence)
        account.signers = resp.raw_data["signers"]
        account.thresholds = thresholds
        return account

    def __check_memo_required_sync(self, transaction: Transaction) -> None:
        if isinstance(transaction, FeeBumpTransaction):
            transaction = transaction.inner_transaction_envelope.transaction
        if not (transaction.memo is None or isinstance(transaction.memo, NoneMemo)):
            return
        for index, destination in self.__get_check_memo_required_destinations(
            transaction
        ):
            if destination.startswith(MUXED_ACCOUNT_STARTING_LETTER):
                continue
            try:
                account_resp = self.accounts().account_id(destination).call()
            except NotFoundError:
                continue
            self.__check_destination_memo(account_resp.raw_data, index, destination)

    async def __check_memo_required_async(
        self, transaction: Union[Transaction, FeeBumpTransaction]
    ) -> None:
        if isinstance(transaction, FeeBumpTransaction):
            transaction = transaction.inner_transaction_envelope.transaction
        if not (transaction.memo is None or isinstance(transaction.memo, NoneMemo)):
            return
        for index, destination in self.__get_check_memo_required_destinations(
            transaction
        ):
            if destination.startswith(MUXED_ACCOUNT_STARTING_LETTER):
                continue
            try:
                account_resp = await self.accounts().account_id(destination).call()
            except NotFoundError:
                continue
            self.__check_destination_memo(account_resp.raw_data, index, destination)

    def __check_destination_memo(
        self, account_resp: dict, index: int, destination: str
    ) -> None:
        memo_required_config_key = "config.memo_required"
        memo_required_config_value = "MQ=="
        data = account_resp["data"]
        if data.get(memo_required_config_key) == memo_required_config_value:
            raise AccountRequiresMemoError(
                "Destination account requires a memo in the transaction.",
                destination,
                index,
            )

    def __get_check_memo_required_destinations(
        self, transaction: Transaction
    ) -> Generator[Tuple[int, str], Any, Any]:
        destinations = set()
        memo_required_operation_code = (
            OperationType.PAYMENT.value,
            OperationType.ACCOUNT_MERGE.value,
            OperationType.PATH_PAYMENT_STRICT_RECEIVE.value,
            OperationType.PATH_PAYMENT_STRICT_SEND.value,
        )
        for index, operation in enumerate(transaction.operations):
            if operation.type_code() in memo_required_operation_code:
                destination: str = operation.destination.account_id
            else:
                continue
            if destination in destinations:
                continue
            destinations.add(destination)
            yield index, destination

    def fetch_base_fee(self) -> Union[int, Coroutine[Any, Any, int]]:
        """Fetch the base fee. Since this hits the server, if the server call fails,
        you might get an error. You should be prepared to use a default value if that happens.

        :return: the base fee
        :raises:
            :exc:`ConnectionError <stellar_sdk.exceptions.ConnectionError>`
            :exc:`NotFoundError <stellar_sdk.exceptions.NotFoundError>`
            :exc:`BadRequestError <stellar_sdk.exceptions.BadRequestError>`
            :exc:`BadResponseError <stellar_sdk.exceptions.BadResponseError>`
            :exc:`UnknownRequestError <stellar_sdk.exceptions.UnknownRequestError>`
        """
        if self.__async:
            return self.__fetch_base_fee_async()
        return self.__fetch_base_fee_sync()

    def __fetch_base_fee_sync(self) -> int:
        latest_ledger = self.ledgers().order(desc=True).limit(1).call()
        base_fee = self.__handle_base_fee(latest_ledger)
        return base_fee

    async def __fetch_base_fee_async(self) -> int:
        latest_ledger = await self.ledgers().order(desc=True).limit(1).call()
        base_fee = self.__handle_base_fee(latest_ledger)
        return base_fee

    def __handle_base_fee(self, latest_ledger: WrappedResponse[LedgerResponse]) -> int:
        base_fee = 100
        if (
            latest_ledger.raw_data["_embedded"]
            and latest_ledger.raw_data["_embedded"]["records"]
            and latest_ledger.raw_data["_embedded"]["records"][0]
        ):
            base_fee = int(
                latest_ledger.raw_data["_embedded"]["records"][0]["base_fee_in_stroops"]
            )
        return base_fee

    def close(self) -> Union[None, Coroutine[Any, Any, None]]:
        """Close underlying connector.

        Release all acquired resources.
        """
        if self.__async:
            return self.__close_async()
        else:
            return self.__close_sync()

    async def __close_async(self) -> None:
        await self._client.close()

    def __close_sync(self) -> None:
        self._client.close()

    async def __aenter__(self) -> "Server":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def __enter__(self) -> "Server":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
