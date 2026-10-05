"""Mode-specific presentation with clearly identified source extracts."""
import re


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]


def unique(items):
    seen = set()
    result = []
    for item in items:
        key = re.sub(r'\W+', ' ', item).strip().lower()
        if key and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def format_summary(mode, overview, summaries, sources):
    points = unique([point for summary in summaries for point in sentences(summary)])
    if mode == 'short':
        return 'SHORT SUMMARY\n\n' + overview
    if mode == 'simple':
        return 'EXPLAIN SIMPLY\n\n' + overview + (
            '\n\nSection explanations\n\n' + '\n\n'.join(f'Section {i+1}\n{s}' for i, s in enumerate(summaries))
            if len(summaries) > 1 else '')
    if mode == 'key_points':
        return 'KEY POINTS\n\nOverview\n' + overview + '\n\n' + '\n'.join('• ' + s for s in points)
    if mode == 'detailed':
        result = 'DETAILED SUMMARY\n\nOverview\n' + overview
        if len(summaries) > 1:
            result += '\n\n' + '\n\n'.join(f'Source section {i+1}\n{s}' for i, s in enumerate(summaries))
    else:
        result = 'EXAM NOTES\n\nOverview\n' + overview
        result += '\n\nImportant concepts\n' + '\n'.join('• ' + s for s in points)
    # Keep these verbatim, label them as extracts, and don't ask the model to
    # reconstruct equations or introduce new examples/definitions.
    definitions, formulas, steps = [], [], []
    for source in sources:
        definitions += [s for s in sentences(source) if re.search(r'\b(is defined as|refers to|means|is a|is an)\b', s, re.I)]
        formulas += [line.strip() for line in source.splitlines() if re.search(r'[=≤≥∑∫]', line)]
        steps += [line.strip() for line in source.splitlines() if re.match(r'^\s*\d+[.)]\s+', line)]
    for heading, values in [('Definitions — source extracts', definitions), ('Formulas / rules — source extracts', formulas), ('Steps — source extracts', steps)]:
        if values:
            result += '\n\n' + heading + '\n' + '\n'.join('• ' + s for s in unique(values))
    return result
