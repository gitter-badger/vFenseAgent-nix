import Queue

from src.utils import logger


class OperationQueue():
    """ Simple queue specifically for server operations.
    """

    def __init__(self):

        self.queue = Queue.Queue()

        self.op_in_progress = False
        self.paused = False

    def queue_dump(self):
        return [op for op in self.queue.queue]

    def remove(self, operation):
        try:
            self.queue.queue.remove(operation)

            return True
        except Exception as e:
            logger.error(
                "Failed to remove operation from queue: {0}".format(operation)
            )
            logger.exception(e)

            return False

    def put_non_duplicate(self, operation):
        """
        Put the operation in queue if no other operation of the same type
        exists.
        """
        if operation.type in [op.type for op in self.queue_dump()]:
            return False

        return self.put(operation)

    def _put_front(self, operation):
        new_queue = Queue.Queue()
        new_queue.put(operation)

        for op in self.queue_dump():
            new_queue.put(operation)

        # +1 to take in to account the newest operation added to the front
        new_queue.unfinished_tasks = self.queue.unfinished_tasks + 1

        self.queue = new_queue

    def put(self, operation, put_front=False):
        """
        Attempts to add an item to the queue.

        Args:
            operation (SofOperation): Operation to be added.

        Kwargs:
            put_front (bool): Determines whether the operation be placed
                in the front of the queue or in the back.

        Returns:
            True if item was successfully added, false otherwise.
        """
        result = False

        try:
            if operation:
                if put_front:
                    self._put_front(operation)
                else:
                    self.queue.put(operation)

                result = True

                try:
                    logger.debug(
                        "Added ({0}, {1}) to queue."
                        .format(operation.type, operation.id)
                    )
                except Exception:
                    logger.debug(
                        "Added {0} to queue."
                        .format(operation)
                    )

        except Queue.Full as e:

            logger.error("Agent is busy. Ignoring operation.")
            result = False

        except Exception as e:

            logger.error("Error adding operation to queue.")
            logger.error("Message: %s" % e)
            result = False

        return result

    def get(self):
        """
        Attempts to get an operation from the queue if no operation is pending.

        Returns:
            The operation if it was successfully retrieved, None otherwise.

        """
        operation = None

        if (not self.op_in_progress) and (not self.paused):

            try:
                operation = self.queue.get_nowait()
                self.op_in_progress = True

                try:
                    logger.debug(
                        "Popping ({0}, {1}) from queue.".format(
                            operation.id, operation.type
                        )
                    )
                except Exception:
                    logger.debug("Popping {0} from queue.".format(operation))

            except Queue.Empty as e:
#                logger.debug("Operations queue is empty.")
                operation = None

            except Exception as e:
                logger.error("Error accessing operation queue.")
                logger.error("Message: %s" % e)
                operation = None

        return operation

    def done(self):
        """
        Indicates that an operation is done.
        @return: Nothing
        """

        try:
            logger.debug("Unfinished tasks before done: {0}".format(self.queue.unfinished_tasks))
            self.queue.task_done()
            logger.debug("Unfinished tasks after done: {0}".format(self.queue.unfinished_tasks))

        except Exception as e:
            logger.error("Error marking operation as done.")
            logger.exception(e)

        finally:
            # Mark as false to continue processing operations
            self.op_in_progress = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_operation_caller(self, callback):
        self.callback = callback

    def _is_op_pending(self, running):
        self.op_in_progress = running
