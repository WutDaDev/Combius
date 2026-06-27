"""Simple dry-run test to simulate a flagged message and exercise
VerificationMonitor.handle_flagged_message without exiting the process.

Run:
python tests/simulate_flag.py
"""

from combius import VerificationMonitor, DiscordAPI

# Create a fake API with a send_message method
class FakeAPI:
    def __init__(self):
        self.sent = []
    def send_message(self, channel_id, content):
        print(f"[FAKE SEND] channel={channel_id} content={content}")
        self.sent.append((channel_id, content))
        return True


def main():
    api = FakeAPI()
    vm = VerificationMonitor(api, channels=["12345"], sound=False)

    sample_msg = {
        'id': '999999999',
        'author': {'id': '1111', 'username': 'OwOBot'},
        'content': '⚠ Are you a human? type the text',
        'attachments': [],
    }

    handled = vm.handle_flagged_message('12345', sample_msg, dry_run=True)
    print('Handled:', handled)

if __name__ == '__main__':
    main()
