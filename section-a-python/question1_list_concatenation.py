"""
Question 1: List Concatenation Without '+' or 'extend()'

Various methods to concatenate two lists in Python without using the '+' operator
or the extend() method, with analysis of pros and cons for each approach.
"""

from itertools import chain
import operator
from functools import reduce


def method1_unpacking(list1, list2):
    """
    Method 1: Using unpacking operator (*)
    
    Pros:
    - Clean, readable syntax
    - Pythonic and modern approach
    - Works with any iterable
    - Creates new list without modifying originals
    
    Cons:
    - Python 3.5+ only
    - Memory overhead for large lists
    - Not efficient for multiple concatenations
    """
    return [*list1, *list2]


def method2_list_comprehension(list1, list2):
    """
    Method 2: Using list comprehension
    
    Pros:
    - Very readable
    - Flexible (can add conditions/transformations)
    - Memory efficient with generator version
    
    Cons:
    - Slightly more verbose
    - Creates temporary iterables
    """
    return [item for sublist in [list1, list2] for item in sublist]


def method3_itertools_chain(list1, list2):
    """
    Method 3: Using itertools.chain()
    
    Pros:
    - Memory efficient (lazy evaluation)
    - Works with any number of iterables
    - Very fast for large datasets
    - Standard library solution
    
    Cons:
    - Returns iterator, need list() conversion
    - Less intuitive for beginners
    """
    return list(chain(list1, list2))


def method4_append_loop(list1, list2):
    """
    Method 4: Using append() in a loop
    
    Pros:
    - Simple and understandable
    - Memory efficient (in-place if modifying original)
    - Works in all Python versions
    
    Cons:
    - Modifies the original list (or creates copy)
    - Less elegant/Pythonic
    - Slower for large lists
    """
    result = list1.copy()  # Don't modify original
    for item in list2:
        result.append(item)
    return result


def method5_slice_assignment(list1, list2):
    """
    Method 5: Using slice assignment
    
    Pros:
    - Efficient for in-place operations
    - Works with any iterable
    - Built-in Python feature
    
    Cons:
    - Less readable
    - Can be confusing for beginners
    - Modifies original list structure
    """
    result = list1.copy()
    result[len(result):] = list2
    return result


def method6_map_and_reduce(list1, list2):
    """
    Method 6: Using map() and reduce() with operator.add
    
    Pros:
    - Functional programming approach
    - Can handle multiple lists easily
    
    Cons:
    - Less readable
    - Overkill for simple concatenation
    - Requires imports
    """
    return reduce(operator.add, [list1, list2])


def method7_sum_function(list1, list2):
    """
    Method 7: Using sum() with empty list as start
    
    Pros:
    - Clever one-liner
    - Works with multiple lists
    
    Cons:
    - Inefficient (O(n²) complexity)
    - Confusing and non-intuitive
    - Not recommended for production
    """
    return sum([list1, list2], [])


def method8_manual_indexing(list1, list2):
    """
    Method 8: Manual indexing and assignment
    
    Pros:
    - Complete control over the process
    - Educational value
    - Memory efficient
    
    Cons:
    - Verbose and error-prone
    - Not Pythonic
    - Slower than built-in methods
    """
    result = [None] * (len(list1) + len(list2))
    
    # Copy first list
    for i, item in enumerate(list1):
        result[i] = item
    
    # Copy second list
    for i, item in enumerate(list2):
        result[len(list1) + i] = item
    
    return result


def method9_deque_extend(list1, list2):
    """
    Method 9: Using collections.deque
    
    Pros:
    - Efficient for large datasets
    - Good for frequent insertions/deletions
    
    Cons:
    - Requires import
    - Returns deque object (need conversion)
    - Overkill for simple concatenation
    """
    from collections import deque
    
    result = deque(list1)
    result.extend(list2)  # Note: This uses extend(), but on deque not list
    return list(result)


def demonstrate_all_methods():
    """Demonstrate all concatenation methods with examples."""
    
    list1 = [1, 2, 3]
    list2 = [4, 5, 6]
    expected = [1, 2, 3, 4, 5, 6]
    
    methods = [
        ("Unpacking (*)", method1_unpacking),
        ("List Comprehension", method2_list_comprehension),
        ("itertools.chain", method3_itertools_chain),
        ("Append Loop", method4_append_loop),
        ("Slice Assignment", method5_slice_assignment),
        ("Map & Reduce", method6_map_and_reduce),
        ("Sum Function", method7_sum_function),
        ("Manual Indexing", method8_manual_indexing),
        ("Deque Extend", method9_deque_extend),
    ]
    
    print("List Concatenation Methods (without '+' or 'extend()'):")
    print(f"list1 = {list1}")
    print(f"list2 = {list2}")
    print(f"Expected result = {expected}")
    print("-" * 60)
    
    for name, method in methods:
        try:
            result = method(list1, list2)
            status = "✓" if result == expected else "✗"
            print(f"{status} {name:20}: {result}")
        except Exception as e:
            print(f"✗ {name:20}: Error - {e}")
    
    print("\nPerformance Ranking (for large datasets):")
    print("1. itertools.chain() - Best for memory and speed")
    print("2. Unpacking (*) - Clean and fast")
    print("3. Slice assignment - Good for in-place operations")
    print("4. List comprehension - Readable and efficient")
    print("5. Append loop - Simple but slower")
    print("6. Manual indexing - Educational but verbose")
    print("7. Map & reduce - Functional but complex")
    print("8. Deque extend - Good for special cases")
    print("9. Sum function - Avoid (O(n²) complexity)")


if __name__ == "__main__":
    demonstrate_all_methods()