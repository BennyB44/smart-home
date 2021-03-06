"""Define automations for security."""
from datetime import time
from enum import Enum
from typing import Union

import voluptuous as vol

from core import APP_SCHEMA, Base
from const import (
    CONF_ENTITY_IDS, CONF_FRIENDLY_NAME, CONF_NOTIFICATION_INTERVAL,
    CONF_PROPERTIES, CONF_STATE)
from helpers import config_validation as cv

CONF_ALARM_CONTROL_PANEL = 'alarm_control_panel'
CONF_GARAGE_DOOR = 'garage_door'
CONF_OVERALL_SECURITY_STATUS = 'overall_security_status_sensor'
CONF_TIME_LEFT_OPEN = 'time_left_open'

HANDLE_GARAGE_OPEN = 'garage_open'


class AbsentInsecure(Base):
    """Define a feature to notify us when we've left home insecure."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITY_IDS: vol.Schema({
            vol.Required(CONF_STATE): cv.entity_id,
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.listen_event(
            self.response_from_push_notification,
            'ios.notification_action_fired',
            actionName='LOCK_UP_AWAY',
            constrain_input_boolean=self.enabled_entity_id,
            action='away')
        self.listen_event(
            self.response_from_push_notification,
            'ios.notification_action_fired',
            actionName='LOCK_UP_HOME',
            constrain_input_boolean=self.enabled_entity_id,
            action='home')
        self.listen_state(
            self.house_insecure,
            self.entity_ids[CONF_STATE],
            new='Open',
            duration=60 * 5,
            constrain_input_boolean=self.enabled_entity_id,
            constrain_noone='just_arrived,home')

    def house_insecure(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Send notifications when the house has been left insecure."""
        self.log('No one home and house is insecure; notifying')

        self.notification_manager.send(
            "No one is home and the house isn't locked up.",
            title='Security Issue 🔐',
            blackout_start_time=None,
            blackout_end_time=None,
            target=['everyone', 'slack'],
            data={'push': {
                'category': 'security'
            }})

    def response_from_push_notification(
            self, event_name: str, data: dict, kwargs: dict) -> None:
        """Respond to 'ios.notification_action_fired' events."""
        target = self.notification_manager.get_target_from_push_id(
            data['sourceDevicePermanentID'])

        if kwargs['action'] == 'home':
            self.turn_on('scene.good_night')
        elif kwargs['action'] == 'away':
            self.turn_on('scene.depart_home')

        self.notification_manager.send(
            '{0} locked up the house.'.format(target.first_name),
            title='Issue Resolved 🔐',
            target=['not {0}'.format(target.first_name), 'slack'])


class AutoDepartureLockup(Base):
    """Define a feature to automatically lock up when we leave."""

    def configure(self) -> None:
        """Configure."""
        self.listen_event(
            self.everyone_gone,
            'PROXIMITY_CHANGE',
            constrain_input_boolean=self.enabled_entity_id)

    def everyone_gone(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Respond to 'PROXIMITY_CHANGE' events."""
        if (not self.security_manager.secure and
                data['old'] == self.presence_manager.ProximityStates.home.value
                and data['new'] !=
                self.presence_manager.ProximityStates.home.value):
            self.log('Everyone has left; locking up')

            self.turn_on('scene.depart_home')


class AutoNighttimeLockup(Base):
    """Define a feature to automatically lock up at night."""

    def configure(self) -> None:
        """Configure."""
        self.run_daily(
            self.midnight,
            time(0, 0, 0),
            constrain_input_boolean=self.enabled_entity_id,
            constrain_anyone='home')

    def midnight(self, kwargs: dict) -> None:
        """Lock up the house at midnight."""
        self.log('Activating "Good Night"')

        self.call_service('scene/turn_on', entity_id='scene.good_night')


class GarageLeftOpen(Base):
    """Define a feature to notify us when the garage is left open."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITY_IDS: vol.Schema({
            vol.Required(CONF_GARAGE_DOOR): cv.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_NOTIFICATION_INTERVAL): int,
            vol.Required(CONF_TIME_LEFT_OPEN): int,
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.listen_event(
            self.response_from_push_notification,
            'ios.notification_action_fired',
            actionName='GARAGE_CLOSE',
            constrain_input_boolean=self.enabled_entity_id)
        self.listen_state(
            self.closed,
            self.entity_ids[CONF_GARAGE_DOOR],
            new='closed',
            constrain_input_boolean=self.enabled_entity_id)
        self.listen_state(
            self.left_open,
            self.entity_ids[CONF_GARAGE_DOOR],
            new='open',
            duration=self.properties[CONF_TIME_LEFT_OPEN],
            constrain_input_boolean=self.enabled_entity_id)

    def closed(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Cancel notification when the garage is closed."""
        if HANDLE_GARAGE_OPEN in self.handles:
            self.handles.pop(HANDLE_GARAGE_OPEN)()  # type: ignore

    def left_open(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Send notifications when the garage has been left open."""
        message = 'The garage has been left open. Want to close it?'

        self.handles[HANDLE_GARAGE_OPEN] = self.notification_manager.repeat(
            message,
            self.properties[CONF_NOTIFICATION_INTERVAL],
            title='Garage Open 🚗',
            blackout_start_time=None,
            blackout_end_time=None,
            target=['everyone'],
            data={'push': {
                'category': 'garage'
            }})

        self.slack_app_home_assistant.ask(
            message, {
                'Yes': {
                    'callback': self.security_manager.close_garage,
                    'response_text': 'You got it; closing it now.'
                },
                'No': {
                    'response_text': 'If you really say so...'
                }
            },
            urgent=True)

    def response_from_push_notification(
            self, event_name: str, data: dict, kwargs: dict) -> None:
        """Respond to 'ios.notification_action_fired' events."""
        self.security_manager.close_garage()

        target = self.notification_manager.get_target_from_push_id(
            data['sourceDevicePermanentID'])
        self.notification_manager.send(
            '{0} closed the garage.'.format(target.first_name),
            title='Issue Resolved 🚗',
            target=['not {0}'.format(target.first_name), 'slack'])


class NotifyOnChange(Base):
    """Define a feature to notify us the secure status changes."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITY_IDS: vol.Schema({
            vol.Required(CONF_STATE): cv.entity_id,
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.listen_state(
            self.state_changed,
            self.entity_ids[CONF_STATE],
            constrain_input_boolean=self.enabled_entity_id)

    def state_changed(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Send a notification when the security state changes."""
        self.log('Notifying of security status change: {0}'.format(new))

        self.notification_manager.send(
            'The security status has changed to "{0}"'.format(new),
            title='Security Change 🔐',
            blackout_start_time=None,
            blackout_end_time=None,
            target=['everyone', 'slack'])


class SecurityManager(Base):
    """Define a class to represent the app."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITY_IDS: vol.Schema({
            vol.Required(CONF_ALARM_CONTROL_PANEL): cv.entity_id,
            vol.Required(CONF_GARAGE_DOOR): cv.entity_id,
            vol.Required(CONF_OVERALL_SECURITY_STATUS): cv.entity_id,
        }, extra=vol.ALLOW_EXTRA),
    })

    class AlarmStates(Enum):
        """Define an enum for alarm states."""

        away = 'armed_away'
        disarmed = 'disarmed'
        home = 'armed_home'

    @property
    def alarm_state(self) -> "AlarmStates":
        """Return the current state of the security system."""
        return self.AlarmStates(
            self.get_state(self.entity_ids[CONF_ALARM_CONTROL_PANEL]))

    @property
    def secure(self) -> bool:
        """Return whether the house is secure or not."""
        return self.get_state(
            self.entity_ids[CONF_OVERALL_SECURITY_STATUS]) == 'Secure'

    def configure(self) -> None:
        """Configure."""
        self.listen_state(
            self._security_system_change_cb,
            self.entity_ids[CONF_ALARM_CONTROL_PANEL])

    def _security_system_change_cb(
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Fire events when the security system status changes."""
        if new != 'unknown':
            self.fire_event('ALARM_CHANGE', state=new)

    def close_garage(self) -> None:
        """Close the garage."""
        self.log('Closing the garage door')

        self.call_service(
            'cover/close_cover', entity_id=self.entity_ids[CONF_GARAGE_DOOR])

    def get_insecure_entities(self) -> list:
        """Return a list of insecure entities."""
        return [
            entity[CONF_FRIENDLY_NAME]
            for entity in self.properties['secure_status_mapping']
            if self.get_state(entity['entity_id']) == entity[CONF_STATE]
        ]

    def open_garage(self) -> None:
        """Open the garage."""
        self.log('Closing the garage door')

        self.call_service(
            'cover.open_cover', entity_id=self.entity_ids[CONF_GARAGE_DOOR])

    def set_alarm(self, new: "AlarmStates") -> None:
        """Set the security system."""
        if new == self.AlarmStates.disarmed:
            self.log('Disarming the security system')

            self.call_service(
                'alarm_control_panel/alarm_disarm',
                entity_id=self.entity_ids[CONF_ALARM_CONTROL_PANEL])
        elif new in (self.AlarmStates.away, self.AlarmStates.home):
            self.log('Arming the security system: "{0}"'.format(new.name))

            self.call_service(
                'alarm_control_panel/alarm_arm_{0}'.format(
                    new.value.split('_')[1]),
                entity_id=self.entity_ids[CONF_ALARM_CONTROL_PANEL])
        else:
            raise AttributeError("Unknown security state: {0}".format(new))
