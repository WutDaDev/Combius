import os
import sys
import unittest

os.environ.setdefault('DISCORD_TOKENS', 'token1')
os.environ.setdefault('CHANNEL_IDS', '1')

sys.path.insert(0, '/workspaces/Combius')
from combius import InventoryParser


class InventoryParserGemTests(unittest.TestCase):
    def test_get_best_gems_uses_quantity_and_does_not_pick_empty_gems(self):
        inv_data = {
            'gem_ids': [51, 56],
            'gem_quantities': {51: 3, 56: 0},
        }

        result = InventoryParser.get_best_gems(inv_data, min_tier=3)

        self.assertEqual(result, [51])

    def test_get_best_gems_prefers_highest_tier_inventory_gems_over_lower_preferred_ids(self):
        inv_data = {
            'gem_ids': [51, 56],
            'gem_quantities': {51: 1, 56: 1},
        }

        result = InventoryParser.get_best_gems(inv_data, min_tier=3, preferred_ids=[51, 52, 53, 56])

        self.assertEqual(result, [56])

    def test_parse_inventory_from_embeds_when_content_is_empty(self):
        messages = [{
            'content': '',
            'author': {'id': '999'},
            'embeds': [{'description': '**Inventory**\n51 × 2 ⠀Common Hunting Gem\n56 × 1 ⠀Legendary Hunting Gem'}],
        }]

        result = InventoryParser.parse(messages, '123')

        self.assertTrue(result['success'])
        self.assertEqual(result['gem_ids'], [51, 56])


if __name__ == '__main__':
    unittest.main()
