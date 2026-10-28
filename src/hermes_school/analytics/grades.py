from collections import defaultdict


def subject_averages(items):
    groups = defaultdict(list)
    for item in items:
        if item['kind'] == 'grades':
            groups[(item['subject'], item['data'].get('period', ''))].append(item)
    results = []
    for (subject, period), grades in groups.items():
        valid = [g for g in grades if g['data'].get('out_of_20') is not None and not g['data'].get('raw', {}).get('nonSignificatif')]
        complete = bool(valid) and all(g['data'].get('coefficient') is not None and g['data']['coefficient'] > 0 for g in valid)
        weight = sum(g['data']['coefficient'] for g in valid) if complete else 0
        results.append({'subject': subject, 'period': period, 'count': len(valid),
                        'average': round(sum(g['data']['out_of_20']*g['data']['coefficient'] for g in valid)/weight, 2) if weight else None,
                        'label': 'Moyenne indicative des notes visibles, pondérées par leurs coefficients connus ; peut différer du bulletin',
                        'sources': [g['id'] for g in valid]})
    return results
