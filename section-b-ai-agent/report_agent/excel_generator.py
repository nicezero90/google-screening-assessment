"""
Simple Excel generation without external dependencies.

This module creates CSV files that can be opened as Excel files.
For a production system, you would use openpyxl or xlsxwriter.
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Any


class SimpleExcelGenerator:
    """Simple Excel-like report generator using CSV format."""
    
    def __init__(self, reports_folder: str = "reports"):
        """Initialize the generator with a reports folder."""
        self.reports_folder = reports_folder
        os.makedirs(reports_folder, exist_ok=True)
    
    def generate_returns_report(self, data: Dict[str, Any], filename: str = None) -> str:
        """
        Generate a comprehensive returns report.
        
        Args:
            data: Analytics data dictionary
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Path to the generated report file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"returns_report_{timestamp}.csv"
        
        filepath = os.path.join(self.reports_folder, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header section
            writer.writerow(["RETURNS & WARRANTY INSIGHTS REPORT"])
            writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([f"Analysis Period: {data.get('period_days', 'N/A')} days"])
            writer.writerow([])  # Empty row
            
            # Summary section
            writer.writerow(["EXECUTIVE SUMMARY"])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Returns", data.get('total_returns', 0)])
            writer.writerow(["Total Loss", f"${data.get('total_loss', 0):.2f}"])
            writer.writerow(["Average Loss per Return", 
                           f"${data.get('total_loss', 0) / max(data.get('total_returns', 1), 1):.2f}"])
            writer.writerow([])  # Empty row
            
            # Product breakdown section
            writer.writerow(["PRODUCT BREAKDOWN"])
            writer.writerow(["Product", "Return Count", "Total Value", "Average Value"])
            
            for product_data in data.get('product_breakdown', []):
                avg_value = product_data['value'] / max(product_data['count'], 1)
                writer.writerow([
                    product_data['product'],
                    product_data['count'],
                    f"${product_data['value']:.2f}",
                    f"${avg_value:.2f}"
                ])
            
            writer.writerow([])  # Empty row
            
            # Reason analysis section
            writer.writerow(["RETURN REASON ANALYSIS"])
            writer.writerow(["Reason", "Count", "Percentage"])
            
            total_reasons = sum(r['count'] for r in data.get('reason_analysis', []))
            for reason_data in data.get('reason_analysis', []):
                percentage = (reason_data['count'] / max(total_reasons, 1)) * 100
                writer.writerow([
                    reason_data['reason'],
                    reason_data['count'],
                    f"{percentage:.1f}%"
                ])
            
            writer.writerow([])  # Empty row
            
            # Recommendations section
            writer.writerow(["RECOMMENDATIONS"])
            recommendations = self._generate_recommendations(data)
            for i, recommendation in enumerate(recommendations, 1):
                writer.writerow([f"{i}.", recommendation])
        
        return filepath
    
    def generate_detailed_report(self, records: List[Dict[str, Any]], 
                               filename: str = None) -> str:
        """
        Generate a detailed report with individual return records.
        
        Args:
            records: List of return records
            filename: Optional filename
            
        Returns:
            Path to the generated report file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detailed_returns_{timestamp}.csv"
        
        filepath = os.path.join(self.reports_folder, filename)
        
        if not records:
            # Create empty report
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["No data available for the selected criteria"])
            return filepath
        
        # Get all unique keys from records
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())
        
        # Define preferred column order
        preferred_order = [
            'id', 'product_name', 'category', 'brand', 'purchase_location',
            'purchase_price', 'original_price', 'discount_percent',
            'purchase_date', 'return_date', 'return_reason', 'warranty_status',
            'customer_id'
        ]
        
        # Order columns
        ordered_keys = []
        for key in preferred_order:
            if key in all_keys:
                ordered_keys.append(key)
                all_keys.remove(key)
        
        # Add any remaining keys
        ordered_keys.extend(sorted(all_keys))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_keys)
            
            # Write header
            writer.writeheader()
            
            # Write records
            for record in records:
                # Clean the record to match fieldnames
                clean_record = {key: record.get(key, '') for key in ordered_keys}
                writer.writerow(clean_record)
        
        return filepath
    
    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the analytics data."""
        recommendations = []
        
        # Analyze return patterns
        product_breakdown = data.get('product_breakdown', [])
        reason_analysis = data.get('reason_analysis', [])
        total_returns = data.get('total_returns', 0)
        
        if total_returns > 0:
            # Top product issues
            if product_breakdown:
                top_product = product_breakdown[0]
                if top_product['count'] > total_returns * 0.3:  # More than 30% of returns
                    recommendations.append(
                        f"Investigate {top_product['product']} quality issues - "
                        f"accounts for {top_product['count']} returns "
                        f"(${top_product['value']:.0f} loss)"
                    )
            
            # Common reasons
            if reason_analysis:
                top_reason = reason_analysis[0]
                total_reasons = sum(r['count'] for r in reason_analysis)
                if top_reason['count'] > total_reasons * 0.4:  # More than 40% of reasons
                    recommendations.append(
                        f"Address '{top_reason['reason']}' issues - "
                        f"responsible for {top_reason['count']} returns"
                    )
            
            # Screen-related issues
            screen_issues = sum(
                r['count'] for r in reason_analysis 
                if 'screen' in r['reason'].lower() or 'cracked' in r['reason'].lower()
            )
            if screen_issues > total_returns * 0.25:  # More than 25%
                recommendations.append(
                    f"Improve packaging/handling - {screen_issues} screen-related returns detected"
                )
            
            # General recommendations
            if total_returns > 10:
                recommendations.append(
                    "Consider implementing pre-delivery quality checks to reduce defective products"
                )
                
                recommendations.append(
                    "Review warranty policies and customer support processes"
                )
        
        if not recommendations:
            recommendations.append("Continue monitoring return patterns for trends")
            recommendations.append("Maintain current quality standards")
        
        return recommendations
    
    def cleanup_old_reports(self, days_old: int = 7):
        """Remove reports older than specified days."""
        import time
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        if os.path.exists(self.reports_folder):
            for filename in os.listdir(self.reports_folder):
                filepath = os.path.join(self.reports_folder, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass  # Ignore errors


# Test function
def test_excel_generator():
    """Test the Excel generator with sample data."""
    generator = SimpleExcelGenerator("test_reports")
    
    # Sample analytics data
    sample_data = {
        'period_days': 14,
        'total_returns': 13,
        'total_loss': 15000,
        'product_breakdown': [
            {'product': 'iPhone 14 Pro', 'count': 5, 'value': 8000},
            {'product': 'iPhone 14', 'count': 3, 'value': 4000},
            {'product': 'iPad Air', 'count': 2, 'value': 3000}
        ],
        'reason_analysis': [
            {'reason': 'Screen cracked out of the box', 'count': 6},
            {'reason': 'Battery issues', 'count': 3},
            {'reason': 'Device not functioning', 'count': 4}
        ]
    }
    
    # Generate reports
    summary_report = generator.generate_returns_report(sample_data)
    print(f"Summary report generated: {summary_report}")
    
    # Sample detailed records
    sample_records = [
        {
            'id': 1,
            'product_name': 'iPhone 14 Pro',
            'purchase_location': 'Apple Store Taipei 101',
            'purchase_price': 35000,
            'return_reason': 'Screen cracked out of the box',
            'return_date': '2024-01-22'
        },
        {
            'id': 2,
            'product_name': 'iPhone 14',
            'purchase_location': 'Online Store',
            'purchase_price': 28000,
            'return_reason': 'Battery not holding charge',
            'return_date': '2024-01-20'
        }
    ]
    
    detailed_report = generator.generate_detailed_report(sample_records)
    print(f"Detailed report generated: {detailed_report}")


if __name__ == "__main__":
    test_excel_generator()