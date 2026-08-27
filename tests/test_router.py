from src.router import Route, route_question


def test_routes_mandatory_sales_questions():
    questions = [
        "What are the top 5 products by total revenue?",
        "What is total revenue by region?",
        "What is the best-selling category by revenue in the 7 days immediately before the latest order date?",
    ]
    assert all(route_question(question) == Route.SALES for question in questions)


def test_routes_policy_questions():
    assert route_question("How long does standard cross-region shipping take?") == Route.DOCUMENTS
    assert route_question("Can I return a stationery item?") == Route.DOCUMENTS
    assert route_question("When do loyalty points expire?") == Route.DOCUMENTS


def test_ambiguous_or_unknown_question_is_controlled():
    assert route_question("Give me an overview") == Route.AMBIGUOUS
    assert route_question("What sales discount policy applies?") == Route.AMBIGUOUS
