"""Define automations for our cars."""
from typing import Union

import voluptuous as vol

from const import (
    CONF_ENTITY_IDS, CONF_FRIENDLY_NAME, CONF_NOTIFICATION_TARGET,
    CONF_PROPERTIES)
from core import APP_SCHEMA, Base
from helpers import config_validation as cv

CONF_CAR = 'car'
CONF_FUEL_THRESHOLD = 'fuel_threshold'

HANDLE_LOW_FUEL = 'low_fuel'


class NotifyLowFuel(Base):
    """Define a feature to notify of the vehicle's ETA to home."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITY_IDS: vol.Schema({
            vol.Required(CONF_CAR): cv.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_FRIENDLY_NAME): str,
            vol.Required(CONF_FUEL_THRESHOLD): int,
            vol.Required(CONF_NOTIFICATION_TARGET): str,
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self):
        """Configure."""
        self.registered = False

        self.listen_state(
            self.low_fuel_found,
            self.entity_ids[CONF_CAR],
            attribute='fuel_level',
            constrain_input_boolean=self.enabled_entity_id)

    def low_fuel_found(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Send a notification when my car is low on gas."""
        try:
            if int(new) < self.properties['fuel_threshold']:
                if self.registered:
                    return

                self.log(
                    'Low fuel detected detected: {0}'.format(
                        self.entity_ids[CONF_CAR]))

                self.registered = True
                self.notification_manager.send(
                    "{0} needs gas; fill 'er up!.".format(
                        self.properties[CONF_FRIENDLY_NAME]),
                    title='{0} is Low ⛽'.format(
                        self.properties[CONF_FRIENDLY_NAME]),
                    target=self.properties[CONF_NOTIFICATION_TARGET])
            else:
                self.registered = False
        except ValueError:
            return
