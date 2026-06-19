def format_top_plans_response(data) -> dict:
    """Format the top plans API response into a user-friendly structure."""
    formatted_response = {
        "capital_guarantee_plans": [],
        "market_linked_plans": [],
        "high_sum_assured_plans": [],
    }

    if not isinstance(data, dict) or data.get("HasError", False):
        return formatted_response

    return_value = data.get("ReturnValue", {})
    if not isinstance(return_value, dict):
        return formatted_response

    def extract_simple_plans(key: str, target_list: list):
        plans = return_value.get(key, [])[:3]
        if isinstance(plans, list):
            for plan in plans:
                if isinstance(plan, dict):
                    target_list.append({
                        "plan_name": plan.get("PlanName", ""),
                        "insurer_name": plan.get("InsurerName", ""),
                        "plan_id": plan.get("PlanID", ""),
                    })

    extract_simple_plans("Cg", formatted_response["capital_guarantee_plans"])
    extract_simple_plans("Ml", formatted_response["market_linked_plans"])
    extract_simple_plans("Hsa", formatted_response["high_sum_assured_plans"])

    return formatted_response
