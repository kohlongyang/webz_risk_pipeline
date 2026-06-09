import math


def compute_score(performance_score, domain_rank):
    virality = (performance_score or 0) * 10
    authority = max(0, 10 - math.log10(max(domain_rank, 1))) * 5
    return min(round(virality + authority), 100)
