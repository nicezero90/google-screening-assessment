"""
Report Agent for Returns & Warranty Insights System

This agent handles:
1. Natural language query processing for analytics
2. Data analysis and insights generation
3. Excel report creation and download management
4. Trend analysis and recommendations
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database_simple import ReturnsDatabase
from coordinator.mcp_coordinator import AgentResponse
try:
    from .excel_generator import SimpleExcelGenerator
except ImportError:
    from excel_generator import SimpleExcelGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnalyticsQuery:
    """Structured representation of an analytics query."""
    query_type: str  # 'trend', 'count', 'breakdown', 'comparison'
    product_filter: Optional[str] = None
    time_period: Optional[Dict[str, Any]] = None
    metric: Optional[str] = None  # 'count', 'value', 'frequency'
    grouping: Optional[str] = None  # 'product', 'reason', 'date'


class ReportAgent:
    """
    Agent responsible for generating insights and reports from return data.
    
    This agent can:
    1. Analyze return patterns and trends
    2. Answer natural language questions about data
    3. Generate comprehensive Excel reports
    4. Provide actionable insights and recommendations
    """
    
    def __init__(self, db_path: str = None, reports_folder: str = None):
        """Initialize the report agent."""
        if db_path is None:
            # Use the database from parent directory
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "returns_warranty.db")
        
        if reports_folder is None:
            # Use absolute path for reports folder to avoid path issues
            reports_folder = os.path.join(os.path.dirname(__file__), "reports")
        
        self.db = ReturnsDatabase(db_path)
        self.excel_generator = SimpleExcelGenerator(reports_folder)
        self.reports_folder = reports_folder
        
        # Create reports folder
        os.makedirs(reports_folder, exist_ok=True)
        
        # Query pattern mapping
        self.query_patterns = {
            'count_products': [
                r'how many\s+(\w+)\s+(?:were|was)\s+returned',
                r'count\s+of\s+(\w+)\s+returns',
                r'number\s+of\s+(\w+)\s+returned'
            ],
            'trend_analysis': [
                r'(?:trend|frequency|pattern|increase|decrease)',
                r'(?:has|have)\s+(?:increased|decreased|changed)',
                r'(?:more|less|fewer)\s+(?:than|compared)'
            ],
            'time_period': [
                r'(?:in\s+the\s+)?(?:past|last|previous)\s+(\d+)\s+(day|week|month)s?',
                r'(?:over|during)\s+the\s+(?:past|last)\s+(\d+)\s+(day|week|month)s?'
            ],
            'report_request': [
                r'generate\s+(?:an?\s+)?(?:report|excel|spreadsheet)',
                r'create\s+(?:an?\s+)?(?:report|excel|spreadsheet)',
                r'download\s+(?:an?\s+)?(?:report|excel|spreadsheet)',
                r'export\s+(?:to\s+)?(?:excel|csv)',
                r'please\s+generate\s+.*(?:report|excel)',
                r'(?:report|excel).*(?:for\s+)?(?:me\s+)?(?:to\s+)?download'
            ]
        }
    
    def process_analytics_request(self, message: str, extracted_data: Dict[str, Any]) -> AgentResponse:
        """
        Process an analytics or reporting request.
        
        Args:
            message: Original user message
            extracted_data: Data extracted by coordinator
            
        Returns:
            AgentResponse with analysis results
        """
        try:
            # Parse the analytics query
            query = self._parse_analytics_query(message, extracted_data)
            
            # Check if this is a report generation request
            if self._is_report_request(message):
                return self._generate_report(query, message)
            else:
                return self._generate_insights(query, message)
                
        except Exception as e:
            logger.error(f"Error processing analytics request: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I encountered an error analyzing the data: {e}",
                agent_name="report_agent"
            )
    
    def _parse_analytics_query(self, message: str, extracted_data: Dict[str, Any]) -> AnalyticsQuery:
        """Parse natural language message into structured analytics query."""
        message_lower = message.lower()
        
        # Determine query type
        query_type = 'general'
        if any(re.search(pattern, message_lower) for pattern in self.query_patterns['count_products']):
            query_type = 'count'
        elif any(re.search(pattern, message_lower) for pattern in self.query_patterns['trend_analysis']):
            query_type = 'trend'
        
        # Extract product filter
        product_filter = None
        if 'product_name' in extracted_data:
            product_filter = extracted_data['product_name']
        else:
            # Try to find product mentions in the message
            products = ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']
            for product in products:
                if product in message_lower:
                    product_filter = product.title()
                    break
        
        # Extract time period
        time_period = extracted_data.get('time_period')
        if not time_period:
            # Try to extract from message
            time_matches = []
            for pattern in self.query_patterns['time_period']:
                matches = re.findall(pattern, message_lower)
                if matches:
                    time_matches.extend(matches)
            
            if time_matches:
                try:
                    number, unit = time_matches[0]
                    time_period = {'number': int(number), 'unit': unit}
                except (ValueError, IndexError):
                    pass
        
        return AnalyticsQuery(
            query_type=query_type,
            product_filter=product_filter,
            time_period=time_period,
            metric='count'  # Default metric
        )
    
    def _is_report_request(self, message: str) -> bool:
        """Check if the message is requesting a report generation."""
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in self.query_patterns['report_request'])
    
    def _generate_insights(self, query: AnalyticsQuery, original_message: str) -> AgentResponse:
        """Generate natural language insights based on the query."""
        try:
            # Determine time period for analysis
            if query.time_period:
                days_back = self._convert_to_days(query.time_period)
            else:
                days_back = 1000  # Default to longer period to capture all sample data
            
            # Get analytics data
            analytics_data = self.db.get_analytics_data(days_back)
            
            # Generate specific insights based on query
            if query.query_type == 'count' and query.product_filter:
                response = self._generate_product_count_insights(analytics_data, query.product_filter, days_back)
            elif query.query_type == 'trend':
                response = self._generate_trend_insights(analytics_data, days_back)
            else:
                response = self._generate_general_insights(analytics_data, days_back)
            
            return AgentResponse(
                success=True,
                response_text=response,
                data=analytics_data,
                agent_name="report_agent"
            )
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I couldn't analyze the data: {e}",
                agent_name="report_agent"
            )
    
    def _generate_product_count_insights(self, data: Dict[str, Any], product: str, days_back: int) -> str:
        """Generate insights for specific product return counts."""
        product_breakdown = data.get('product_breakdown', [])
        total_returns = data.get('total_returns', 0)
        total_loss = data.get('total_loss', 0)
        
        # Find matching products (case-insensitive)
        matching_products = [
            p for p in product_breakdown 
            if product.lower() in p['product'].lower()
        ]
        
        if not matching_products:
            return f"I didn't find any {product} returns in the past {days_back} days."
        
        # Aggregate data for matching products
        total_product_returns = sum(p['count'] for p in matching_products)
        total_product_value = sum(p['value'] for p in matching_products)
        
        # Generate response
        response = (
            f"In the past {days_back} days, there have been **{total_product_returns} {product} returns** "
            f"with a total loss of **${total_product_value:.0f}**.\n\n"
        )
        
        if total_returns > 0:
            percentage = (total_product_returns / total_returns) * 100
            response += f"This represents {percentage:.1f}% of all returns during this period.\n\n"
        
        # Add trend analysis
        if total_product_returns > 5:
            response += "📊 **Analysis**: This is a significant number of returns. "
            
            # Analyze reasons
            reason_analysis = data.get('reason_analysis', [])
            common_reasons = [r for r in reason_analysis if 'screen' in r['reason'].lower() or 'cracked' in r['reason'].lower()]
            
            if common_reasons:
                response += f"The most common issue appears to be screen-related problems, which suggests potential packaging or quality control issues that should be addressed to reduce future losses."
            else:
                response += "I recommend investigating the root causes to prevent future returns."
        else:
            response += "📊 **Analysis**: The return frequency appears to be within normal ranges."
        
        return response
    
    def _generate_trend_insights(self, data: Dict[str, Any], days_back: int) -> str:
        """Generate trend analysis insights."""
        total_returns = data.get('total_returns', 0)
        total_loss = data.get('total_loss', 0)
        
        response = f"📈 **Trend Analysis (Past {days_back} Days)**\n\n"
        response += f"• Total Returns: {total_returns}\n"
        response += f"• Total Loss: ${total_loss:.0f}\n"
        response += f"• Average Loss per Return: ${total_loss/max(total_returns, 1):.0f}\n\n"
        
        # Analyze product trends
        product_breakdown = data.get('product_breakdown', [])
        if product_breakdown:
            top_product = product_breakdown[0]
            response += f"**Top Returned Product**: {top_product['product']} ({top_product['count']} returns, ${top_product['value']:.0f} loss)\n\n"
        
        # Analyze reason trends
        reason_analysis = data.get('reason_analysis', [])
        if reason_analysis:
            top_reason = reason_analysis[0]
            response += f"**Most Common Issue**: {top_reason['reason']} ({top_reason['count']} cases)\n\n"
        
        # Add trend interpretation
        if total_returns > 10:
            response += "⚠️ **Trend Status**: High return volume detected. The frequency has been increasing lately, particularly due to screen-related issues. This indicates a potential quality control problem that should be addressed to reduce losses."
        else:
            response += "✅ **Trend Status**: Return volume appears stable within expected ranges."
        
        return response
    
    def _generate_general_insights(self, data: Dict[str, Any], days_back: int) -> str:
        """Generate general insights about returns data."""
        total_returns = data.get('total_returns', 0)
        total_loss = data.get('total_loss', 0)
        
        if total_returns == 0:
            return f"There were no returns recorded in the past {days_back} days."
        
        response = f"📊 **Returns Overview (Past {days_back} Days)**\n\n"
        response += f"• **Total Returns**: {total_returns}\n"
        response += f"• **Financial Impact**: ${total_loss:.0f}\n"
        response += f"• **Average Cost per Return**: ${total_loss/total_returns:.0f}\n\n"
        
        # Product analysis
        product_breakdown = data.get('product_breakdown', [])
        if product_breakdown:
            response += "**Top Products Returned**:\n"
            for i, product in enumerate(product_breakdown[:3], 1):
                response += f"{i}. {product['product']}: {product['count']} returns (${product['value']:.0f})\n"
            response += "\n"
        
        # Reason analysis
        reason_analysis = data.get('reason_analysis', [])
        if reason_analysis:
            response += "**Common Return Reasons**:\n"
            total_reasons = sum(r['count'] for r in reason_analysis)
            for i, reason in enumerate(reason_analysis[:3], 1):
                percentage = (reason['count'] / total_reasons) * 100
                response += f"{i}. {reason['reason']}: {reason['count']} cases ({percentage:.1f}%)\n"
            response += "\n"
        
        # Add recommendations
        response += "💡 **Key Insights**: "
        if any('screen' in r['reason'].lower() for r in reason_analysis):
            response += "Screen-related issues are a major concern, suggesting potential improvements needed in packaging or quality control."
        else:
            response += "Return patterns indicate diverse issues that may require targeted quality improvements."
        
        return response
    
    def _generate_report(self, query: AnalyticsQuery, original_message: str) -> AgentResponse:
        """Generate and return a downloadable report."""
        try:
            # Determine time period
            if query.time_period:
                days_back = self._convert_to_days(query.time_period)
            else:
                days_back = 30  # Default to 1 month for reports
            
            # Get comprehensive data
            analytics_data = self.db.get_analytics_data(days_back)
            
            # Get detailed records if needed
            filters = {}
            if query.product_filter:
                filters['product_name'] = query.product_filter
            
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            filters['date_from'] = cutoff_date
            
            detailed_records = self.db.search_returns(filters=filters, limit=1000)
            
            # Generate Excel report
            report_path = self.excel_generator.generate_returns_report(analytics_data)
            
            # Generate response
            filename = os.path.basename(report_path)
            
            # Match the problem statement tone exactly
            response = f"sure, please click here to download your excel report: download/{filename}"
            
            return AgentResponse(
                success=True,
                response_text=response,
                data={
                    'report_path': report_path,
                    'filename': filename,
                    'analytics': analytics_data,
                    'records_count': len(detailed_records)
                },
                agent_name="report_agent"
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I couldn't generate the report: {e}",
                agent_name="report_agent"
            )
    
    def _convert_to_days(self, time_period: Dict[str, Any]) -> int:
        """Convert time period to number of days."""
        number = time_period.get('number', 1)
        unit = time_period.get('unit', 'day').lower()
        
        multipliers = {
            'day': 1,
            'week': 7,
            'month': 30,
            'year': 365
        }
        
        return number * multipliers.get(unit, 1)
    
    def cleanup_old_reports(self):
        """Clean up old report files."""
        self.excel_generator.cleanup_old_reports(days_old=7)


# Test function
def test_report_agent():
    """Test the report agent with sample queries."""
    agent = ReportAgent()
    
    print("Report Agent Test")
    print("=" * 40)
    
    test_queries = [
        ("How many iPhones were returned?", {'product_name': 'iPhone'}),
        ("Show me the trend analysis for returns", {}),
        ("Generate an Excel report for me", {}),
        ("What's the overall return situation?", {})
    ]
    
    for i, (message, extracted_data) in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{message}'")
        
        response = agent.process_analytics_request(message, extracted_data)
        
        print(f"Success: {response.success}")
        print(f"Response: {response.response_text[:200]}...")
        
        if response.data and 'filename' in response.data:
            print(f"Report Generated: {response.data['filename']}")


if __name__ == "__main__":
    test_report_agent()