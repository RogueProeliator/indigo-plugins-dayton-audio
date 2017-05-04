# Introduction
This Indigo 6.0+ plugin allows Indigo to control the DAX66 6-Source/6-Zone Distributed Audio System from [Dayton Audio](http://www.daytonaudio.com/). Thanks to a robust protocol, this plugin is able to both read and set nearly every aspect of the receiver such as zone power, volume, treble, bass, and more.

# Hardware Requirements
This plugin works exclusively with the DAX66 6-Source/6-Zone Distributed Audio System. It supports daisy-chain configuration for multiple receivers (one master and up to two connected slaves) as well as having multiple master receivers on the network. You will need a serial connection from any master receiver to your computer.

# Installation and Configuration
### Obtaining the Plugin
The latest released version is always available on the Releases tab and is the recommended version to use for your system. Alternatively, you may wish to download the source of this repository which includes all files necessary to install and utilize the plugin.

### Configuring the Plugin
Upon first installation you will be asked to configure the plugin; please see the instructions on the configuration screen for more information. Most users will be fine with the defaults unless an email is desired when a new version is released.<br />
![Plugin Configuration Screen](<Documentation/Help/PluginConfigurationScreen.png>)

# Plugin Devices
### Master Receiver(s)
You will need to create a new Dayton Audio Zone Receiver for each master receiver that you have connected to Indigo via serial connection; any slave units connected to the master will automatically be available for control (these show up as additional available zones in Indigo).<br />
![Receiver Configuration Screen](<Documentation/Help/ReceiverDeviceConfigScreen.png>)

### Individual Zones
After you have created the Indigo devices for your receiver, you will need to create an Indigo device for each zone attached to the receiver that you wish to monitor or control. These zone devices are where you will control the output of the receiver via actions and states.<br />
![Zone Configuration Screen](<Documentation/Help/ZoneDeviceConfigScreen.png>)

# Available Device states
The plugin tracks several device states where are updated according to the polling frequency of the master receiver. Note that after each action, the appropriate zone is updated immediately. The following zone states are supported:

- **isPoweredOn** - tracks the power state of the zone (_true / false_)
- **source** - The selected source number for the zone (_1 - 6_)
- **isMuted** - Whether or not the zone is currently muted (_true / false_)
- **volume** - The volume level for the zone (_0 - 38_)
- **bassLevel** - The level of bass selected for the zone (_0 - 14_)
- **trebleLevel** - The level of treble selected for the zone (_0 - 14_)
- **balanceStatus** - The left-right balance selected for the zone (_0 - 20_)
- **brightnessLevel** - This is the value / display value of the dimmer control; it will show and set a volume level appropriately scaled to the device
- **onOffState** - The default status state of the dimmer, this will mimic the isPoweredOn state for visibility within Indigo interfaces

# Available Actions
### Receiver Actions
- **Set Power (All Zones)** - This action will turn on/off all of the zones connected to a master receiver.
- **Set Source (All Zones)** - This action will set the input of all connected zones to the selected source.

### Zone actions
- **Set Zone Source** - Sets the input source for the zone
- **Zone Volume - Set Value** - Set the volume of the zone to the provided Value
- **Zone Volume - Adjust Up/Down** - This adjusts the volume from its current state up/down; note you will need to make sure the device is polling often enough if you have the keypads or IR remote in use
- **Zone Mute - Set** - Explicitly sets the zone to either mute or not muted
- **Zone Mute - Toggle** - Toggles the mute/unmuted status of the zone; note you will need to make sure the device is polling often enough if you have the keypads or IR remote in use
- **Zone Treble - Set Value** - Sets the treble level for the zone
- **Zone Bass - Set Value** - Sets the bass level for the zone
- **Zone Balance - Set Value** - Sets the balance for the zone
