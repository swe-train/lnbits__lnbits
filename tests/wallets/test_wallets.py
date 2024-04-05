import importlib

import pytest
from mock import Mock
from pytest_mock.plugin import MockerFixture

from lnbits.core.models import BaseWallet
from tests.helpers import (
    FundingSourceConfig,
    WalletTest,
    rest_wallet_fixtures_from_json,
)

wallets_module = importlib.import_module("lnbits.wallets")


class DataObject:
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])


def build_test_id(test: WalletTest):
    return f"{test.funding_source}.{test.function}({test.description})"


def fn_factory(data: str):
    def f1(*args, **kwargs):
        return data

    return f1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_data",
    rest_wallet_fixtures_from_json("tests/wallets/fixture2.json"),
    ids=build_test_id,
)
async def test_wallets(mocker: MockerFixture, test_data: WalletTest):
    # print("### test_data", dict(test_data))
    print("######## test ########", test_data.description)
    if test_data.skip:
        pytest.skip()

    for mock in test_data.mocks:
        print("### mock", mock)

        return_value = {}
        for field_name in mock.response:
            field = mock.response[field_name]
            response_type = field["response_type"]
            request_type = field["request_type"]
            response = field["response"]

            if request_type == "function":
                if response_type == "data":
                    response = _dict_to_object(response)
                return_value[field_name] = fn_factory(response)
            elif request_type == "data":
                return_value[field_name] = _dict_to_object(response)
            elif request_type == "json":
                return_value[field_name] = response

        m = _data_mock(return_value)
        mocker.patch(mock.method, m)

    wallet: BaseWallet = _load_funding_source(test_data.funding_source)
    status = await wallet.status()

    print("#### wallet.status", status)

    assert status.error_message is None
    assert status.balance_msat == 55000


def _load_funding_source(funding_source: FundingSourceConfig) -> BaseWallet:
    custom_settings = funding_source.settings
    original_settings = {}

    settings = getattr(wallets_module, "settings")

    for s in custom_settings:
        original_settings[s] = getattr(settings, s)
        setattr(settings, s, custom_settings[s])

    fs_instance: BaseWallet = getattr(wallets_module, funding_source.wallet_class)()

    # rollback settings (global variable)
    for s in original_settings:
        setattr(settings, s, original_settings[s])

    return fs_instance


def _dict_to_object(data: dict) -> DataObject:
    d = {**data}
    for k in data:
        value = data[k]
        if isinstance(value, dict):
            d[k] = _dict_to_object(value)

    return DataObject(**d)


def _data_mock(data: dict) -> Mock:
    return Mock(return_value=_dict_to_object(data))
