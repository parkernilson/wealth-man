from typing import Callable, TypeVar
import datetime as dt
from enum import Enum
from abc import ABC, abstractmethod
from functools import reduce
import bisect


class Action:
    def __init__(self, value: int):
        self.value = value
        self.action_name = None

    def __str__(self):
        return f"{self.__class__.__name__}({self.value})"


class DepositAction(Action):
    def __init__(self, value: int):
        super().__init__(value)


class Sequence:
    def __init__(self, timed_actions: tuple[dt.date, Action]):
        self.timed_actions = timed_actions

    def __str__(self):
        def gen_list():
            for date, action in self.timed_actions:
                yield f"{date}: {str(action)}"

        return "\n".join(gen_list())


class Interval:
    def __init__(self, dates: list[dt.date]):
        self.dates = dates


class AccountBase:
    def __init__(self, name: str, interest_rate: int):
        self.name = name
        self.interest_rate = interest_rate


class Context:
    def __init__(
        self, accounts: dict[str, "Account"], start_date: dt.date, end_date: dt.date
    ):
        self.accounts = accounts
        self.start_date = start_date
        self.end_date = end_date


Formula = TypeVar("Formula", bound=Callable[[Context], Sequence])


class Account:
    def __init__(self, initial_value: float, account_base: AccountBase, formula: Formula):
        self.formula = formula
        self.value = initial_value


class Freq(Enum):
    DAILY = 0
    WEEKLY = 1

Results = TypeVar("Results", bound=dict[dt.date, float])

class Scenario:
    def __init__(self, context: Context):
        self.context = context

    def solve(self, resolution: Freq) -> Results:
        # for each account, generate the sequences
        sequences = [
            # add the account_id to each sequence event
            map(lambda action: (action, account_id), self.context.accounts[account_id].formula(self.context))
            for account_id in self.context.accounts
        ]
        # combine the sequences into one sequence (keeping track of which account it is for)
        combined_sequence = sorted(reduce(lambda x, y: x + y, sequences))
        # generate the ticks base on resolution
        tick_dates = every(resolution)(self.context)
        # resolve the actions in the combined sequence between each tick of resolution
        results: Results = dict()
        action_offset = 0
        for tick_date in tick_dates:
            # find the index where the combined_sequence[0] date is greater than the tick_date[0] date
            next_index = bisect.bisect_left(combined_sequence, tick_date, lo=action_offset)
            cur_actions = combined_sequence[action_offset:next_index]

            # process each action
            for action in cur_actions:
                if isinstance(action[0], DepositAction):
                    account_id = action[1]
                    self.context.accounts[account_id].value += action[0].value
                    # TODO: calculate interest

            action_offset = next_index
            results[tick_date] = {
                [account_id]: self.context.accounts[account_id].value
                for account_id in self.context.accounts
            }
        return results

def Pattern(*ops: Callable[[Context], any]) -> Formula:
    def formulate(ctx: Context):
        cur = ops[0](ctx)
        for i in range(0, len(ops) - 1):
            next = ops[i + 1](ctx)
            cur = next(cur)
        return cur

    return formulate

class IntervalDates:
    def __init__(self, start_date: dt.date, end_date: dt.date):
        self.start_date = start_date
        self.end_date = end_date

def generate_dates(start_date, end_date, timedelta):
    cur_date = start_date
    while cur_date < end_date:
        yield cur_date
        cur_date += timedelta

def create_interval(freq: Freq) -> Callable[[tuple[dt.date, dt.date]], Interval]:
    def _create_interval(dates: tuple[dt.date, dt.date]):
        (start_date, end_date) = dates
        timedelta = {
            Freq.DAILY: dt.timedelta(days=1),
            Freq.WEEKLY: dt.timedelta(weeks=1),
        }.get(freq)
        dates = list(generate_dates(start_date, end_date, timedelta))
        return Interval(dates)
    return _create_interval

def every(freq: Freq) -> Callable[[Context], Interval]:
    def formulate(ctx: Context):
        start_date = ctx.start_date
        end_date = ctx.end_date
        return create_interval(freq)((start_date, end_date))
    return formulate

def deposit(value: int) -> Callable[[Context], Callable[[Interval], Sequence]]:
    def formulate(ctx: Context):
        def transform(interval: Interval) -> Sequence:
            def generate_list():
                for date in interval.dates:
                    yield (date, DepositAction(value))

            timed_actions = list(generate_list())
            return Sequence(timed_actions=timed_actions)

        return transform

    return formulate


formula_1 = Pattern(every(Freq.WEEKLY), deposit(500))

ctx = Context(dt.date(2023, 1, 1), dt.date(2024, 1, 1))

sequence = formula_1(ctx)

account_1_id = "account1"
account_1_base = AccountBase("Account 1", 5)

scenario = Scenario(
    context=Context(
        accounts={
            [account_1_id]: Account(account_base=account_1_base, formula=formula_1)
        }
    )
)

scenario.solve(resolution=Freq.DAILY)
