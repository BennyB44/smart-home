"""Define automations for Amazon Dash Buttons."""
# pylint: disable=too-few-public-methods,unused-argument

from automation import Automation  # type: ignore


class ButtonAction:
    """Define a base class for button actions."""

    def __init__(self, hass: Automation, args: dict) -> None:
        """Initialize."""
        self._args = args
        self._hass = hass

    def run(self) -> None:
        """Run the action."""
        raise NotImplementedError()


class ActivateScene(ButtonAction):
    """Define an action that turns on a scene."""

    def run(self) -> None:
        """Turn on the scene."""
        self._hass.turn_on('scene.{0}'.format(self._args['scene']))


class ArmSecuritySystem(ButtonAction):
    """Define an action that sets the security system in "Home" mode."""

    def run(self) -> None:
        """Set the security system."""
        try:
            state = self._hass.security_manager.States[self._args['state']]
        except KeyError:
            self._hass.error('Unknown state: {0}'.format(self._args['state']))

        self._hass.security_manager.state = state


class BumpClimate(ButtonAction):
    """Define an action that bumps the climate 2° in the correct direction."""

    def run(self) -> None:
        """Bump."""
        degrees = self._args['degrees']
        current_mode = self._hass.climate_manager.mode

        if current_mode == self._hass.climate_manager.Modes.cool:
            degrees *= -1

        self._hass.climate_manager.indoor_temp += degrees


class ToggleEntity(ButtonAction):
    """Toggle an entity."""

    def run(self) -> None:
        """Toggle."""
        entity = self._args['entity']
        domain = entity.split('.')[0]

        self._hass.call_service('{0}/toggle'.format(domain), entity_id=entity)


class DashButton(Automation):
    """Define an automation for Amazon Dash Buttons."""

    OBJECT_MAP = {
        'Activate "Good Night"': (ActivateScene, {
            'scene': 'good_night'
        }),
        'Arm Security System "Home"': (ArmSecuritySystem, {
            'state': 'home'
        }),
        'Bump Climate 2°': (BumpClimate, {
            'degrees': 2
        }),
        'Toggle Christmas Tree': (
            ToggleEntity, {
                'entity': 'switch.christmas_tree'
            }),
        'Toggle Master Bedroom Salt Lamp': (
            ToggleEntity, {
                'entity': 'light.salt_lamp_master_bedroom'
            }),
    }

    @property
    def action_list(self) -> str:
        """Return the action input select for this button."""
        return self.entities['action_list']

    @action_list.setter
    def action_list(self, value: str) -> None:
        """Set the action input select for this button."""
        self.select_option(self.entities['action_list'], value)

    def initialize(self) -> None:
        """Initialize."""
        super().initialize()

        self.listen_event(
            self.button_pressed,
            'AMAZON_DASH_PRESS',
            button_label=self.properties['friendly_name'])

    def button_pressed(
            self, event_name: str, data: dict, kwargs: dict) -> None:
        """Respond when button is pressed."""
        action_name = self.get_state(self.entities['action_list'])

        if action_name not in self.OBJECT_MAP:
            self.error('Unknown action: {0}'.format(action_name))
            return

        self.log('Running Dash action: {0}'.format(action_name))

        klass, args = self.OBJECT_MAP[action_name]
        button = klass(self, args)  # type: ignore
        button.run()
