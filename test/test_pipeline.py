"""Tests for the nprintML Pipeline"""
import argparse
import unittest

from nprintml import pipeline

import nprintml.net.step
import nprintml.label.step
import nprintml.learn.step


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.parser = argparse.ArgumentParser()

    def test_eager_ordering(self):
        "pipeline determines step ordering upon inst'n and so extends parser"
        self.assertEqual(len(self.parser._action_groups), 2)

        pline = pipeline.Pipeline(self.parser)

        self.assertEqual(len(self.parser._action_groups), 5)

        for (defining_word, action_group) in zip(
            ('network', 'label', 'automl'),
            self.parser._action_groups[2:],
        ):
            self.assertIn(defining_word, action_group.title)

        pipeline_steps = [type(step) for step in pline]
        self.assertSequenceEqual(pipeline_steps, (
            nprintml.net.step.Net,
            nprintml.label.step.Label,
            nprintml.learn.step.Learn,
        ))
