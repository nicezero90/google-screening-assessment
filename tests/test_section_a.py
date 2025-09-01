"""
Unit tests for Section A - Python Coding Questions

Tests for:
1. List concatenation methods
2. Base-N to decimal conversion function
"""

import unittest
import sys
import os

# Add the section-a-python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'section-a-python'))

from question1_list_concatenation import (
    method1_unpacking,
    method2_list_comprehension,
    method3_itertools_chain,
    method4_append_loop,
    method5_slice_assignment,
    method6_map_and_reduce,
    method7_sum_function,
    method8_manual_indexing,
    method9_deque_extend
)

from question2_base_conversion import base_n_to_decimal


class TestListConcatenation(unittest.TestCase):
    """Test cases for Question 1: List concatenation methods."""
    
    def setUp(self):
        """Set up test data."""
        self.list1 = [1, 2, 3]
        self.list2 = [4, 5, 6]
        self.expected = [1, 2, 3, 4, 5, 6]
        
        self.empty_list = []
        self.single_item = [42]
        self.mixed_types = ['a', 1, None]
        
        # All concatenation methods to test
        self.methods = [
            ("method1_unpacking", method1_unpacking),
            ("method2_list_comprehension", method2_list_comprehension),
            ("method3_itertools_chain", method3_itertools_chain),
            ("method4_append_loop", method4_append_loop),
            ("method5_slice_assignment", method5_slice_assignment),
            ("method6_map_and_reduce", method6_map_and_reduce),
            ("method7_sum_function", method7_sum_function),
            ("method8_manual_indexing", method8_manual_indexing),
            ("method9_deque_extend", method9_deque_extend),
        ]
    
    def test_basic_concatenation(self):
        """Test basic list concatenation with all methods."""
        for method_name, method in self.methods:
            with self.subTest(method=method_name):
                result = method(self.list1, self.list2)
                self.assertEqual(result, self.expected, 
                               f"{method_name} failed basic concatenation")
    
    def test_empty_lists(self):
        """Test concatenation with empty lists."""
        for method_name, method in self.methods:
            with self.subTest(method=method_name):
                # Empty + non-empty
                result1 = method(self.empty_list, self.list1)
                self.assertEqual(result1, self.list1, 
                               f"{method_name} failed with empty first list")
                
                # Non-empty + empty
                result2 = method(self.list1, self.empty_list)
                self.assertEqual(result2, self.list1, 
                               f"{method_name} failed with empty second list")
                
                # Empty + empty
                result3 = method(self.empty_list, self.empty_list)
                self.assertEqual(result3, [], 
                               f"{method_name} failed with both lists empty")
    
    def test_single_item_lists(self):
        """Test concatenation with single-item lists."""
        for method_name, method in self.methods:
            with self.subTest(method=method_name):
                result = method(self.single_item, self.single_item)
                self.assertEqual(result, [42, 42], 
                               f"{method_name} failed with single-item lists")
    
    def test_mixed_types(self):
        """Test concatenation with mixed data types."""
        numbers = [1, 2, 3]
        for method_name, method in self.methods:
            with self.subTest(method=method_name):
                result = method(self.mixed_types, numbers)
                expected = ['a', 1, None, 1, 2, 3]
                self.assertEqual(result, expected, 
                               f"{method_name} failed with mixed types")
    
    def test_original_lists_unchanged(self):
        """Test that original lists are not modified."""
        original_list1 = self.list1.copy()
        original_list2 = self.list2.copy()
        
        for method_name, method in self.methods:
            with self.subTest(method=method_name):
                method(self.list1, self.list2)
                self.assertEqual(self.list1, original_list1, 
                               f"{method_name} modified first original list")
                self.assertEqual(self.list2, original_list2, 
                               f"{method_name} modified second original list")


class TestBaseConversion(unittest.TestCase):
    """Test cases for Question 2: Base-N to decimal conversion."""
    
    def test_provided_examples(self):
        """Test the specific examples provided in the question."""
        # Valid examples
        self.assertAlmostEqual(base_n_to_decimal("101.11", "binary"), 5.75)
        self.assertAlmostEqual(base_n_to_decimal("17.4", "octal"), 15.5)
        self.assertAlmostEqual(base_n_to_decimal("123.456", "decimal"), 123.456)
        
        # Invalid example should raise ValueError
        with self.assertRaises(ValueError):
            base_n_to_decimal("1G.F", "hex")
    
    def test_binary_conversion(self):
        """Test binary to decimal conversion."""
        test_cases = [
            ("0", 0.0),
            ("1", 1.0),
            ("10", 2.0),
            ("11", 3.0),
            ("1010", 10.0),
            ("0.1", 0.5),
            ("0.01", 0.25),
            ("1.1", 1.5),
            ("101.101", 5.625),
        ]
        
        for binary_str, expected in test_cases:
            with self.subTest(binary=binary_str):
                result = base_n_to_decimal(binary_str, "binary")
                self.assertAlmostEqual(result, expected, places=10)
    
    def test_octal_conversion(self):
        """Test octal to decimal conversion."""
        test_cases = [
            ("0", 0.0),
            ("7", 7.0),
            ("10", 8.0),
            ("17", 15.0),
            ("777", 511.0),
            ("0.4", 0.5),
            ("1.4", 1.5),
        ]
        
        for octal_str, expected in test_cases:
            with self.subTest(octal=octal_str):
                result = base_n_to_decimal(octal_str, "octal")
                self.assertAlmostEqual(result, expected, places=10)
    
    def test_hexadecimal_conversion(self):
        """Test hexadecimal to decimal conversion."""
        test_cases = [
            ("A", 10.0),
            ("F", 15.0),
            ("10", 16.0),
            ("FF", 255.0),
            ("100", 256.0),
            ("A.8", 10.5),
            ("F.F", 15.9375),
        ]
        
        for hex_str, expected in test_cases:
            with self.subTest(hex=hex_str):
                result = base_n_to_decimal(hex_str, "hex")
                self.assertAlmostEqual(result, expected, places=10)
    
    def test_decimal_conversion(self):
        """Test decimal to decimal conversion (identity)."""
        test_cases = [
            ("0", 0.0),
            ("123", 123.0),
            ("456.789", 456.789),
            ("0.001", 0.001),
        ]
        
        for decimal_str, expected in test_cases:
            with self.subTest(decimal=decimal_str):
                result = base_n_to_decimal(decimal_str, "decimal")
                self.assertAlmostEqual(result, expected, places=10)
    
    def test_negative_numbers(self):
        """Test negative number conversion."""
        test_cases = [
            ("-1", "decimal", -1.0),
            ("-101", "binary", -5.0),
            ("-10", "octal", -8.0),
            ("-A", "hex", -10.0),
            ("-1.5", "decimal", -1.5),
        ]
        
        for number_str, base_name, expected in test_cases:
            with self.subTest(number=number_str, base=base_name):
                result = base_n_to_decimal(number_str, base_name)
                self.assertAlmostEqual(result, expected, places=10)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Zero in different representations
        zero_cases = [("0", "binary"), ("0", "octal"), ("0", "decimal"), ("0", "hex")]
        for zero_str, base_name in zero_cases:
            with self.subTest(zero=zero_str, base=base_name):
                result = base_n_to_decimal(zero_str, base_name)
                self.assertEqual(result, 0.0)
        
        # Fractional only numbers
        self.assertAlmostEqual(base_n_to_decimal(".5", "decimal"), 0.5)
        self.assertAlmostEqual(base_n_to_decimal(".1", "binary"), 0.5)
        
        # Large numbers
        large_binary = "1" * 10  # 1023 in decimal
        result = base_n_to_decimal(large_binary, "binary")
        self.assertEqual(result, 1023.0)
    
    def test_invalid_inputs(self):
        """Test invalid input handling."""
        # Invalid base names
        with self.assertRaises(ValueError):
            base_n_to_decimal("123", "invalid_base")
        
        # Invalid digits for base
        invalid_cases = [
            ("2", "binary"),      # 2 is invalid in binary
            ("8", "octal"),       # 8 is invalid in octal
            ("G", "hex"),         # G is invalid in hex
            ("A", "decimal"),     # A is invalid in decimal
        ]
        
        for invalid_str, base_name in invalid_cases:
            with self.subTest(invalid=invalid_str, base=base_name):
                with self.assertRaises(ValueError):
                    base_n_to_decimal(invalid_str, base_name)
        
        # Empty string
        with self.assertRaises(ValueError):
            base_n_to_decimal("", "decimal")
        
        # Multiple decimal points
        with self.assertRaises(ValueError):
            base_n_to_decimal("1.2.3", "decimal")
        
        # Invalid characters
        with self.assertRaises(ValueError):
            base_n_to_decimal("1@2", "decimal")
    
    def test_type_validation(self):
        """Test input type validation."""
        # Non-string inputs
        with self.assertRaises(TypeError):
            base_n_to_decimal(123, "decimal")
        
        with self.assertRaises(TypeError):
            base_n_to_decimal("123", 10)
    
    def test_base_name_variations(self):
        """Test different base name formats."""
        # Test case insensitivity and abbreviations
        variations = [
            ("BINARY", "binary"),
            ("Binary", "binary"),
            ("bin", "binary"),
            ("OCTAL", "octal"),
            ("oct", "octal"),
            ("DECIMAL", "decimal"),
            ("dec", "decimal"),
            ("HEX", "hex"),
            ("hexadecimal", "hex"),
        ]
        
        for variation, standard in variations:
            with self.subTest(variation=variation):
                result1 = base_n_to_decimal("10", variation)
                result2 = base_n_to_decimal("10", standard)
                self.assertEqual(result1, result2)
    
    def test_whitespace_handling(self):
        """Test whitespace handling in inputs."""
        test_cases = [
            ("  123  ", "decimal", 123.0),
            (" 101 ", "binary", 5.0),
            ("A ", "hex", 10.0),
            (" binary ", "binary"),
        ]
        
        # Test number string whitespace
        for i in range(len(test_cases) - 1):
            number_str, base_name, expected = test_cases[i]
            with self.subTest(number=repr(number_str)):
                result = base_n_to_decimal(number_str, "decimal" if i == 0 else base_name)
                self.assertAlmostEqual(result, expected)
        
        # Test base name whitespace
        result = base_n_to_decimal("101", " binary ")
        self.assertAlmostEqual(result, 5.0)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)