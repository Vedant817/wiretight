from app.integrations.rate_budget import RateBudget


def test_ids_share_endpoint_budget_and_twenty_requests_share_global_budget():
    now = [0.0]
    waits = []

    def sleep(delay):
        waits.append(delay)
        now[0] += delay

    budget = RateBudget(clock=lambda: now[0], sleep=sleep)
    for number in range(11):
        budget.acquire("/transfers/" + str(number))
    assert waits == [1.0]
    now[0] = 0.0
    waits.clear()
    budget = RateBudget(clock=lambda: now[0], sleep=sleep)
    for number in range(21):
        budget.acquire("/resource" + str(number))
    assert waits == [1.0]
