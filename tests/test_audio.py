from _common import *

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)


class TestSpeak(BaseSpielTest):
    def _setup_custom_sink(self):
        bin = Gst.Bin.new("bin")
        level = Gst.ElementFactory.make("level", "level")
        bin.add(level)
        sink = Gst.ElementFactory.make("fakesink", "sink")
        bin.add(sink)
        level.link(sink)

        level.set_property("post-messages", True)
        # level.set_property("interval", 100)
        sink.set_property("sync", True)

        pad = level.get_static_pad("sink")
        ghostpad = Gst.GhostPad.new("sink", pad)
        bin.add_pad(ghostpad)

        speechSynthesis = Spiel.Speaker.new_sync(None)
        speechSynthesis.props.sink = bin

        pipeline = bin.get_parent()
        bus = pipeline.get_bus()

        return speechSynthesis, bus

    def test_max_volume(self):
        loop = GLib.MainLoop()

        def _on_message(bus, message):
            info = message.get_structure()
            if info.get_name() == "level":
                self.assertGreater(info.get_value("rms")[0], -5)
                loop.quit()

        speechSynthesis, bus = self._setup_custom_sink()

        bus.connect("message::element", _on_message)

        utterance = Spiel.Utterance(text="hello world, how are you?")
        utterance.props.volume = 1
        utterance.props.voice = self.get_voice(
            speechSynthesis, "org.mock2.Speech.Provider", "gmw/en-US"
        )

        speechSynthesis.speak(utterance)

        loop.run()

    def test_half_volume(self):
        loop = GLib.MainLoop()

        def _on_message(bus, message):
            info = message.get_structure()
            if info.get_name() == "level":
                self.assertLess(info.get_value("rms")[0], -5)
                loop.quit()

        speechSynthesis, bus = self._setup_custom_sink()

        bus.connect("message::element", _on_message)

        utterance = Spiel.Utterance(text="hello world, how are you?")
        utterance.props.volume = 0.5
        utterance.props.voice = self.get_voice(
            speechSynthesis, "org.mock2.Speech.Provider", "gmw/en-US"
        )
        speechSynthesis.speak(utterance)

        loop.run()

    def test_change_volume(self):
        loop = GLib.MainLoop()

        levels = []

        def _on_message(bus, message):
            info = message.get_structure()
            if info.get_name() == "level":
                level = info.get_value("rms")[0]
                if level > -5:
                    levels.append(level)
                    utterance.props.volume = 0.5
                else:
                    levels.append(level)
                    loop.quit()

        speechSynthesis, bus = self._setup_custom_sink()

        bus.connect("message::element", _on_message)

        utterance = Spiel.Utterance(text="hello world, how are you?")
        utterance.props.volume = 1.0
        utterance.props.voice = self.get_voice(
            speechSynthesis, "org.mock2.Speech.Provider", "gmw/en-US"
        )
        speechSynthesis.speak(utterance)

        loop.run()
        self.assertGreater(levels[0], -5)
        self.assertLess(levels[1], -5)

    def test_queue(self):
        # Tests the proper disposal/closing of 'audio/x-spiel' utterances in a queue
        speaker = Spiel.Speaker.new_sync(None)

        sink = Gst.ElementFactory.make("autoaudiosink", "sink")
        # Override usual test fakesink
        speaker.props.sink = sink

        voice = self.get_voice(speaker, "org.mock2.Speech.Provider", "gmw/en-US")
        [one, two] = [
            Spiel.Utterance(text=text, voice=voice) for text in ["silent", "silent"]
        ]

        expected_events = [
            ["notify:speaking", True],
            ["utterance-started", one],
            ["utterance-finished", one],
            ["utterance-started", two],
            ["utterance-finished", two],
            ["notify:speaking", False],
        ]

        actual_events = self.capture_speak_sequence(speaker, one, two)

        self.assertEqual(actual_events, expected_events)


if __name__ == "__main__":
    test_main()
