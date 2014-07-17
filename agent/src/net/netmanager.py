import os
import json
import requests

from src.utils import settings, logger, RepeatTimer
from serveroperation.sofoperation import OperationKey, OperationValue, \
    RequestMethod, ResponseUris


_message_delimiter = '<EOF>'

allow_checkin = True


class NetManager():
    """Used to talk to the server."""

    def __init__(self, seconds_to_checkin=60):
        """
        Args:
            seconds_to_checkin (int): Defines the interval, in seconds, to
            check-in to the server. Defaults to 60 seconds.
        """

        self._server_url = 'https://{0}:{1}/'.format(
            settings.ServerAddress, settings.ServerPort
        )

        self._timer = RepeatTimer(seconds_to_checkin, self._agent_checkin)

    def start(self):
        """Starts the repeating timer that checks-in to the server at the
        set interval.
        """
        self._timer.start()

    def incoming_callback(self, callback):
        """Sets the callback to be used when operations were received during
        agent check-in.

        Args:
            callback (function): The function which will be called back on
                server response. This function must accept one dictionary
                argument.

        """
        self._incoming_callback = callback

    def _get_response_uri(self, operation_type):
        response_uri = ResponseUris.get_response_uri(operation_type)

        if not response_uri:
            raise Exception(
                "Could not get response_uri for {0}"
                .format(operation_type)
            )

        return response_uri

    def _get_request_method(self, operation_type):
        response_uri = ResponseUris.get_request_method(operation_type)

        if not response_uri:
            raise Exception(
                "Could not get request_method for {0}"
                .format(operation_type)
            )

        return response_uri

    def _agent_checkin(self):
        """Checks in to the server to retrieve all pending operations."""

        if allow_checkin and settings.AgentId:
            root = {
                OperationKey.Operation: OperationValue.CheckIn,
                OperationKey.OperationId: '',
                OperationKey.AgentId: settings.AgentId
            }

            try:
                success = self.send_message_register_response(
                    json.dumps(root),
                    self._get_response_uri(OperationValue.CheckIn),
                    self._get_request_method(OperationValue.CheckIn)
                )

            except Exception as err:
                logger.error(
                    "Could not check in to the server due to an exception."
                )
                logger.exception(err)

            if not success:
                logger.error(
                    "Could not check-in to server; received a non-200 status "
                    "code. Check all server and agent logs for more details."
                )

        else:
            logger.info("Checkin set to false, or no agent id.")

    def _get_callable_request_method(self, req_method):
        """Use to get the appropriate request method to talk to the server.

        Args:
            (str) req_method: The request method that is wanted
                (Ex: POST, PUT, GET)

        Returns:
            (func/Exception) The corresponding requests method that matches
            what was passed in arguments. Throws an exception if no request
            method found.
        """
        if req_method.upper() == RequestMethod.POST:
            return requests.post
        if req_method.upper() == RequestMethod.PUT:
            return requests.put
        if req_method.upper() == RequestMethod.GET:
            return requests.get

        raise Exception(
            "Could not get request method for {0}"
            .format(req_method)
        )

    def send_message(self, data, uri, req_method):
        """Sends a message to the server and waits for data in return.

        Args:
            data (str): JSON formatted str to send the server.
            uri (str): RESTful uri to send the data.
            req_method (str): HTTP Request Method.

        Returns:
            (bool, dict) A 2-tuple that contains the success from sending the
            message (False if received non-200), and a dictionary containing
            the response from the server.
        """

        url = os.path.join(self._server_url, uri)
        headers = {
            'Content-Type': 'application/json',
            'Authentication': {'token': settings.Token}
        }

        if settings.AgentId:
            headers['Authentication']['agent_id'] = settings.AgentId

        sent = False
        received_data = {}

        logger.debug("Sending message to: {0}".format(url))
        logger.debug("Message being sent: {0}".format(data))

        try:
            request_method = self._get_callable_request_method(req_method)

            response = request_method(
                url,
                data=data,
                headers=headers,
                verify=False,
                timeout=30
            )

            logger.debug("Status code: %s " % response.status_code)
            logger.debug("Server text: %s " % response.text)

            if response.status_code == 200:
                sent = True

            try:
                received_data = response.json()

            except Exception as e:
                logger.error("Unable to read data from server. Invalid JSON?")
                logger.exception(e)

        except Exception as e:
            logger.error("Unable to send data to server.")
            logger.exception(e)

        return sent, received_data

    def send_message_register_response(self, data, uri, req_method):
        """Send message to server and register the response by using the
        incoming callback method that has been set.

        Args:
            data (str): JSON formatted str to send the server.
            uri (str): RESTful uri to send the data.
            req_method (str): HTTP Request Method

        Returns:
            (bool) The success of sending the message to the server. False on
            non-200 status code.
        """
        success, received_data = self.send_message(data, uri, req_method)

        if received_data:
            logger.debug(
                "Placing received data into the incoming callback method."
            )
            self._incoming_callback(received_data)

        else:
            logger.debug("Received empty data after sending message.")

        return success
