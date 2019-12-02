from seldon_core.seldon_client import (
    SeldonClient,
    SeldonClientPrediction,
    SeldonClientCombine,
)
from unittest import mock
from seldon_core.utils import (
    array_to_grpc_datadef,
    seldon_message_to_json,
    json_to_seldon_message,
)
from seldon_core.proto import prediction_pb2, prediction_pb2_grpc
import numpy as np
import json

JSON_TEST_DATA = {"test": [0.0, 1.0]}


class MockResponse:
    def __init__(self, json_data, status_code, reason="", text=""):
        self.json_data = json_data
        self.status_code = status_code
        self.reason = reason
        self.text = text

    def json(self):
        return self.json_data


def mocked_requests_post_404(url, *args, **kwargs):
    return MockResponse(None, 404, "Not Found")


def mocked_requests_post_success(url, *args, **kwargs):
    data = np.random.rand(1, 1)
    datadef = array_to_grpc_datadef("tensor", data)
    request = prediction_pb2.SeldonMessage(data=datadef)
    json = seldon_message_to_json(request)
    return MockResponse(json, 200, text="{}")


def mocked_requests_post_success_json_data(url, *args, **kwargs):
    request = json_to_seldon_message({"jsonData": JSON_TEST_DATA})
    json = seldon_message_to_json(request)
    return MockResponse(json, 200, text="{}")


def mock_get_token(
    oauth_key: str = "",
    oauth_secret: str = "",
    namespace: str = None,
    endpoint: str = "localhost:8002",
):
    return "1234"


@mock.patch("requests.post", side_effect=mocked_requests_post_404)
def test_predict_rest_404(mock_post):
    sc = SeldonClient(deployment_name="404")
    response = sc.predict()
    assert response.success == False
    assert response.msg == "404:Not Found"


@mock.patch("requests.post", side_effect=mocked_requests_post_success)
def test_predict_rest(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict()
    print(mock_post.call_args)
    assert response.success == True
    assert response.response.data.tensor.shape == [1, 1]
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success)
def test_predict_rest_with_names(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(names=["a", "b"])
    assert mock_post.call_args[1]["json"]["data"]["names"] == ["a", "b"]
    assert response.success == True
    assert response.response.data.tensor.shape == [1, 1]
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success_json_data)
def test_predict_rest_json_data_ambassador(mock_post):
    sc = SeldonClient(deployment_name="mymodel", gateway="ambassador")
    response = sc.predict(json_data=JSON_TEST_DATA)
    json_response = seldon_message_to_json(response.response)
    assert "jsonData" in mock_post.call_args[1]["json"]
    assert mock_post.call_args[1]["json"]["jsonData"] == JSON_TEST_DATA
    assert response.success is True
    assert json_response["jsonData"] == JSON_TEST_DATA
    assert mock_post.call_count == 1


@mock.patch("seldon_core.seldon_client.get_token", side_effect=mock_get_token)
@mock.patch("requests.post", side_effect=mocked_requests_post_success_json_data)
def test_predict_rest_json_data_seldon(mock_post, mock_token):
    sc = SeldonClient(deployment_name="mymodel", gateway="seldon")
    response = sc.predict(json_data=JSON_TEST_DATA)
    json_response = seldon_message_to_json(response.response)
    assert "jsonData" in mock_post.call_args[1]["json"]
    assert mock_post.call_args[1]["json"]["jsonData"] == JSON_TEST_DATA
    assert response.success is True
    assert json_response["jsonData"] == JSON_TEST_DATA
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success_json_data)
def test_explain_rest_json_data_ambassador(mock_post):
    sc = SeldonClient(deployment_name="mymodel", gateway="ambassador")
    response = sc.explain(json_data=JSON_TEST_DATA)
    json_response = seldon_message_to_json(response.response)
    # Currently this doesn't need to convert to JSON due to #1083
    # i.e. json_response = seldon_message_to_json(response.response)
    assert "jsonData" in mock_post.call_args[1]["json"]
    assert mock_post.call_args[1]["json"]["jsonData"] == JSON_TEST_DATA
    assert json_response["jsonData"] == JSON_TEST_DATA
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success)
def test_predict_rest_with_ambassador_prefix(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(
        gateway="ambassador", transport="rest", gateway_prefix="/mycompany/ml"
    )
    assert mock_post.call_args[0][0].index("/mycompany/ml") > 0
    assert response.success == True
    assert response.response.data.tensor.shape == [1, 1]
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success)
def test_predict_microservice_rest(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.microservice(method="predict")
    print(response)
    assert response.success == True
    assert response.response.data.tensor.shape == [1, 1]
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success_json_data)
def test_predict_microservice_rest_json_data(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.microservice(method="predict", json_data=JSON_TEST_DATA)
    json_response = seldon_message_to_json(response.response)
    assert "jsonData" in mock_post.call_args[1]["data"]["json"]
    assert response.success is True
    assert mock_post.call_args[1]["data"]["json"] == json.dumps(
        {"jsonData": JSON_TEST_DATA}
    )
    assert json_response["jsonData"] == JSON_TEST_DATA
    assert mock_post.call_count == 1


@mock.patch("requests.post", side_effect=mocked_requests_post_success)
def test_feedback_microservice_rest(mock_post):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.microservice_feedback(
        prediction_request=prediction_pb2.SeldonMessage(),
        prediction_response=prediction_pb2.SeldonMessage(),
        reward=1.0,
    )
    print(response)
    assert response.success == True
    assert response.response.data.tensor.shape == [1, 1]
    assert mock_post.call_count == 1


class MyStub(object):
    def __init__(self, channel):
        self.channel = channel

    def Predict(self, **kwargs):
        return prediction_pb2.SeldonMessage(strData="predict")

    def TransformInput(selfself, **kwargs):
        return prediction_pb2.SeldonMessage(strData="transform-input")

    def TransformOutput(selfself, **kwargs):
        return prediction_pb2.SeldonMessage(strData="transform-output")

    def Route(selfself, **kwargs):
        return prediction_pb2.SeldonMessage(strData="route")


def mock_grpc_stub_predict(channel):
    return MyStub()


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.SeldonStub", new=MyStub)
def test_predict_grpc_ambassador():
    sc = SeldonClient(deployment_name="mymodel", transport="grpc", gateway="ambassador")
    response = sc.predict()
    assert response.response.strData == "predict"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.SeldonStub", new=MyStub)
def test_grpc_predict_json_data_ambassador():
    sc = SeldonClient(deployment_name="mymodel", transport="grpc", gateway="ambassador")
    response = sc.predict(json_data=JSON_TEST_DATA)
    assert response.response.strData == "predict"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.SeldonStub", new=MyStub)
@mock.patch("seldon_core.seldon_client.get_token", side_effect=mock_get_token)
def test_predict_grpc_seldon(mock_get_token):
    sc = SeldonClient(deployment_name="mymodel", transport="grpc", gateway="seldon")
    response = sc.predict()
    assert response.response.strData == "predict"
    assert mock_get_token.call_count == 1


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.SeldonStub", new=MyStub)
@mock.patch("seldon_core.seldon_client.get_token", side_effect=mock_get_token)
def test_grpc_predict_json_data_seldon(mock_get_token):
    sc = SeldonClient(deployment_name="mymodel", transport="grpc", gateway="seldon")
    response = sc.predict(json_data=JSON_TEST_DATA)
    assert response.response.strData == "predict"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.ModelStub", new=MyStub)
def test_predict_grpc_microservice_predict():
    sc = SeldonClient(transport="grpc")
    response = sc.microservice(method="predict")
    assert response.response.strData == "predict"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.GenericStub", new=MyStub)
def test_predict_grpc_microservice_transform_input():
    sc = SeldonClient(transport="grpc")
    response = sc.microservice(method="transform-input")
    assert response.response.strData == "transform-input"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.GenericStub", new=MyStub)
def test_predict_grpc_microservice_transform_output():
    sc = SeldonClient(transport="grpc")
    response = sc.microservice(method="transform-output")
    assert response.response.strData == "transform-output"


@mock.patch("seldon_core.seldon_client.prediction_pb2_grpc.GenericStub", new=MyStub)
def test_predict_grpc_microservice_transform_route():
    sc = SeldonClient(transport="grpc")
    response = sc.microservice(method="route")
    assert response.response.strData == "route"


#
# Wiring Tests
#


@mock.patch(
    "seldon_core.seldon_client.microservice_api_rest_seldon_message",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_microservice_api_rest_seldon_message(mock_handler):
    sc = SeldonClient()
    response = sc.microservice(transport="rest", method="predict")
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.microservice_api_rest_aggregate",
    return_value=SeldonClientCombine(None, None),
)
def test_wiring_microservice_api_rest_aggregate(mock_handler):
    sc = SeldonClient()
    response = sc.microservice(transport="rest", method="aggregate")
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.microservice_api_rest_feedback",
    return_value=SeldonClientCombine(None, None),
)
def test_wiring_microservice_api_rest_feedback(mock_handler):
    sc = SeldonClient()
    response = sc.microservice_feedback(
        prediction_pb2.SeldonMessage(),
        prediction_pb2.SeldonMessage(),
        1.0,
        transport="rest",
    )
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.microservice_api_grpc_seldon_message",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_microservice_api_grpc_seldon_message(mock_handler):
    sc = SeldonClient()
    response = sc.microservice(transport="grpc", method="predict")
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.microservice_api_grpc_aggregate",
    return_value=SeldonClientCombine(None, None),
)
def test_wiring_microservice_api_grpc_aggregate(mock_handler):
    sc = SeldonClient()
    response = sc.microservice(transport="grpc", method="aggregate")
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.microservice_api_grpc_feedback",
    return_value=SeldonClientCombine(None, None),
)
def test_wiring_microservice_api_grpc_feedback(mock_handler):
    sc = SeldonClient()
    response = sc.microservice_feedback(
        prediction_pb2.SeldonMessage(),
        prediction_pb2.SeldonMessage(),
        1.0,
        transport="grpc",
    )
    assert mock_handler.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.rest_predict_gateway",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_rest_predict_ambassador(mock_rest_predict_ambassador):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(gateway="ambassador", transport="rest")
    assert mock_rest_predict_ambassador.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.grpc_predict_gateway",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_grpc_predict_ambassador(mock_grpc_predict_ambassador):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(gateway="ambassador", transport="grpc")
    assert mock_grpc_predict_ambassador.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.rest_predict_seldon_oauth",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_rest_predict_seldon_oauth(mock_rest_predict_seldon_oauth):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(gateway="seldon", transport="rest")
    assert mock_rest_predict_seldon_oauth.call_count == 1


@mock.patch(
    "seldon_core.seldon_client.grpc_predict_seldon_oauth",
    return_value=SeldonClientPrediction(None, None),
)
def test_wiring_grpc_predict_seldon_oauth(mock_grpc_predict_seldon_oauth):
    sc = SeldonClient(deployment_name="mymodel")
    response = sc.predict(gateway="seldon", transport="grpc")
    assert mock_grpc_predict_seldon_oauth.call_count == 1
