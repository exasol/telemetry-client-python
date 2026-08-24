"""
Protocol definition of the messages we're sending to the server.
"""

import dataclasses
import time
import typing as tt

# Version of the protocol
VERSION = "0.2"

# Name of the feature
Feature = str

# Timestamp of the measurement
Timestamp = tt.Union[int, float]

# Collection of features accumulated
Features = tt.Dict[Feature, tt.List[Timestamp]]


@dataclasses.dataclass(frozen=True)
class Message:
    """
    Top level message to the server.
    """

    # Version of the protocol this message corresponds to.
    version: str

    # Name of the product
    category: str

    # Version of the product
    productVersion: str

    # Current unit timestamp when the message was created
    # (used by the server to get the age of the individual reports)
    timestamp: Timestamp

    # Collection of features we've got so far
    features: Features

    def to_json(self) -> dict:
        return {
            "version": self.version,
            "category": self.category,
            "productVersion": self.productVersion,
            "timestamp": self.timestamp,
            "features": self.features,
        }

    @classmethod
    def from_features(cls, category: str, productVersion: str, features: Features) -> "Message":
        """
        Construct the message object from collected features.
        We're not deep copy of features, just store the reference of it.
        :param features: collection of features
        :param category: name of the product
        :param productVersion: version of the product
        :return: Message created
        """
        return Message(
            version=VERSION,
            category=category,
            productVersion=productVersion,
            timestamp=get_current_ts(),
            features=features,
        )


def get_current_ts() -> Timestamp:
    """
    Get current timestamp.
    """
    return int(time.time())
