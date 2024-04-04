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

        d = {}
        for k in mock.response:
            response_type = mock.response[k]["response_type"]
            response = mock.response[k]["response"]
            if response_type == "function":
                d[k] = fn_factory(response)
            elif response_type == "data":
                d[k] = _data_mock(response)
            elif response_type == "json":
                d[k] = response


            request_type = mock.request_type
            m = d  # default to json
            if request_type == "function":
                m = fn_factory(d)
            elif request_type == "data":
                m = _data_mock(d)

        print("### data1", d)
        m = _data_mock(d)
        if mock.request_type == "function":
            print("#### mocker.patch", mock.method)
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
