"""
Smart Exam-Preparation Schedular
-Phase 1: Priority scoring engine

Formula: priority score = (topic weight x weakness factor ) / days until exam
higher score = sooner study
"""
from dataclasses import dataclass
from datetime import date

@dataclass 
class Topic:
    id: int = None
    name: str = ""
    subject: str = ""
    weight: int = 0     #in terms of rating 1-5 based on importance 
    weakness: int = 0   #in terms of rating like 1-5 cofident to very weak
    exam_date: str = ""  # stored as "YYYY-MM-DD"
    done: bool = False

    def days_until_exam(self) -> int:
        exam = date.fromisoformat(self.exam_date)
        today = date.today()
        return max((exam - today).days, 1)

    def score(self, pace: int) -> float:
        days_left = self.days_until_exam()
        pace_adjustment = pace / 2
        return (self.weight * self.weakness * pace_adjustment) / days_left
    
def rank_topics(topics: list[Topic], pace: int) -> list[Topic]:
        """
        return only unfinished topics, sorted highest priority first
        """
        pending = [t for t in topics if not t.done]
        return sorted(pending, key=lambda t: t.score(pace), reverse=True)

def build_schedule(topics: list[Topic], hours_per_day: float, pace: int) -> list[tuple[Topic, float]]:
    """
    split today's available hours across pending topics,
    proportional to their priority score
    """
    ranked = rank_topics(topics, pace)
    if not ranked:
        return []

    total_score = sum(t.score(pace) for t in ranked)
    if total_score == 0:
         share = hours_per_day / len(ranked)
         return [(t, round(share, 2)) for t in ranked]

    return [
         (t, round(hours_per_day * (t.score(pace) / total_score), 2))
         for t in ranked
    ]

def print_schedule(topics: list[Topic], hours_per_day: float, pace: int) -> None:
    schedule = build_schedule(topics, hours_per_day, pace)
    print(f"\nToday's plan ({hours_per_day} hours available):\n")
    for topic, hours in schedule:
        print(f"  {topic.name:<20} [{topic.subject:<12}] "
              f"score={topic.score(pace):.2f}  ->  {hours} hrs")
    print()

if __name__ == "__main__":
    from datetime import timedelta

    def days_from_now(n):
        return (date.today() + timedelta(days=n)).isoformat()

    topics = [
        Topic(name="Deadlocks", subject="OS", weight=4, weakness=5, exam_date=days_from_now(5)),
        Topic(name="Scheduling Algorithms", subject="OS", weight=5, weakness=3, exam_date=days_from_now(5)),
        Topic(name="Conditional Probability", subject="Probability", weight=3, weakness=4, exam_date=days_from_now(4)),
        Topic(name="Inheritance", subject="C++", weight=3, weakness=2, exam_date=days_from_now(2)),
        Topic(name="Polymorphism", subject="Java", weight=3, weakness=1, exam_date=days_from_now(2)),
    ]

    my_pace = 3
    print_schedule(topics, hours_per_day=4, pace=my_pace)

    topics[0].done = True
    print("--- After marking 'Deadlocks' complete ---")
    print_schedule(topics, hours_per_day=4, pace=my_pace)