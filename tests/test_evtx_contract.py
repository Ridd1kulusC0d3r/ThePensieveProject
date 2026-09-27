import unittest

from pensieve_timeline.parsers.evtx import parse_evtx_xml
from pensieve_timeline.scoring import score_event


SYSMON_XML = """<?xml version="1.0" encoding="utf-8"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Sysmon" Guid="{11111111-1111-1111-1111-111111111111}" />
    <EventID>1</EventID>
    <Version>5</Version>
    <Level>4</Level>
    <Task>1</Task>
    <Opcode>0</Opcode>
    <Keywords>0x8000000000000000</Keywords>
    <TimeCreated SystemTime="2026-01-01T10:00:00.123456Z" />
    <EventRecordID>42</EventRecordID>
    <Correlation ActivityID="{22222222-2222-2222-2222-222222222222}" />
    <Execution ProcessID="900" ThreadID="901" />
    <Channel>Microsoft-Windows-Sysmon/Operational</Channel>
    <Computer>LAB-WIN-01</Computer>
    <Security UserID="S-1-5-18" />
  </System>
  <EventData>
    <Data Name="User">LAB\\alice</Data>
    <Data Name="ProcessId">4242</Data>
    <Data Name="Image">C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe</Data>
    <Data Name="Hash">SHA256=aaa</Data>
    <Data Name="Hash">MD5=bbb</Data>
  </EventData>
</Event>
"""

USERDATA_XML = """<?xml version="1.0" encoding="utf-8"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Example-Provider" />
    <EventID>100</EventID>
    <TimeCreated SystemTime="2026-01-01T11:00:00Z" />
    <EventRecordID>7</EventRecordID>
    <Execution ProcessID="77" ThreadID="88" />
    <Channel>Application</Channel>
    <Computer>LAB-WIN-02</Computer>
  </System>
  <UserData>
    <ExampleEvent xmlns="urn:example">
      <UserName>bob</UserName>
      <Item>one</Item>
      <Item>two</Item>
    </ExampleEvent>
  </UserData>
</Event>
"""

NON_SYSMON_EVENT_ONE = """<?xml version="1.0" encoding="utf-8"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Not-Sysmon" />
    <EventID>1</EventID>
    <TimeCreated SystemTime="2026-01-01T12:00:00Z" />
    <EventRecordID>8</EventRecordID>
    <Channel>Application</Channel>
    <Computer>LAB-WIN-03</Computer>
  </System>
  <EventData>
    <Data Name="Message">ordinary provider event</Data>
  </EventData>
</Event>
"""


class EvtxContractTests(unittest.TestCase):
    def test_sysmon_xml_preserves_system_and_duplicate_event_data(self):
        event = parse_evtx_xml(
            SYSMON_XML,
            source_path="sample.evtx",
            fallback_index=1,
        )

        self.assertEqual(event.parser, "python-evtx")
        self.assertEqual(event.parser_version, "2")
        self.assertEqual(event.provider, "Microsoft-Windows-Sysmon")
        self.assertEqual(event.event_code, "1")
        self.assertEqual(event.host, "LAB-WIN-01")
        self.assertEqual(event.user, r"LAB\alice")
        self.assertEqual(event.pid, "4242")
        self.assertEqual(event.record_locator, "event_record_id:42")

        self.assertEqual(
            event.raw["system"]["execution_process_id"],
            "900",
        )
        self.assertEqual(
            event.raw["system"]["security_user_id"],
            "S-1-5-18",
        )
        self.assertEqual(
            event.raw["event_data"]["Hash"],
            ["SHA256=aaa", "MD5=bbb"],
        )
        self.assertEqual(len(event.raw["xml_sha256"]), 64)

        scored = score_event(event)
        self.assertEqual(scored.risk_score, 10)
        self.assertIn("sysmon-process-create", scored.tags)

    def test_user_data_is_flattened_without_losing_duplicates(self):
        event = parse_evtx_xml(
            USERDATA_XML,
            source_path="application.evtx",
            fallback_index=2,
        )

        self.assertEqual(event.user, "bob")
        self.assertEqual(event.pid, "77")
        self.assertEqual(
            event.raw["user_data"]["Item"],
            ["one", "two"],
        )
        self.assertIn("UserName=bob", event.message)

    def test_event_id_one_from_other_provider_is_not_scored_as_sysmon(self):
        event = parse_evtx_xml(
            NON_SYSMON_EVENT_ONE,
            source_path="other.evtx",
            fallback_index=3,
        )
        scored = score_event(event)

        self.assertEqual(scored.event_code, "1")
        self.assertEqual(scored.risk_score, 0)
        self.assertNotIn("sysmon-process-create", scored.tags)

    def test_invalid_xml_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_evtx_xml(
                "<Event>",
                source_path="broken.evtx",
                fallback_index=4,
            )

    def test_missing_time_fails_closed(self):
        xml = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
          <System>
            <Provider Name="Example" />
            <EventID>5</EventID>
            <EventRecordID>9</EventRecordID>
          </System>
        </Event>"""
        with self.assertRaises(ValueError):
            parse_evtx_xml(
                xml,
                source_path="missing-time.evtx",
                fallback_index=5,
            )


if __name__ == "__main__":
    unittest.main()
