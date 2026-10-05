"""Run all five modes offline on synthetic academic fixtures. No live DB writes.

Outputs actual summaries, timings and sampled process memory for human review.
This is a benchmark, not a claim of automatic factual verification.
"""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import json
from pathlib import Path
import socket
import threading
from time import perf_counter
from unittest.mock import patch
import psutil
from app.services.summarization_service import summarization_service

CS = '''An algorithm is a finite sequence of clearly defined steps for solving a problem. A program implements an algorithm in a programming language. Correctness means that the algorithm produces the required result for every valid input. Efficiency describes the resources it uses, commonly time and memory. Linear search checks items one at a time and works on unsorted data. Binary search repeatedly halves a sorted search interval. Binary search requires sorted input; applying it to unsorted data does not guarantee a correct answer. For a list of n items, linear search has worst-case time O(n), while binary search has worst-case time O(log n). These bounds describe growth as input size increases, rather than elapsed seconds on a particular computer.'''

DBMS = '''Relational databases

A database management system is software that stores, retrieves, and controls access to organized data. A relational database represents data as tables. Each row represents a record and each column represents an attribute. A primary key uniquely identifies a row. A foreign key refers to a key in another table and supports referential integrity. A university database might keep students and courses in separate tables and use an enrollment table to record which students take which courses. Separating these facts prevents a course name from being repeated in every student record.

SQL and query execution

SQL provides operations for querying and updating relational data. A SELECT statement retrieves rows, a WHERE clause restricts which rows match, and a JOIN combines related rows. An index is an auxiliary structure that can speed up suitable searches. An index does not guarantee that every query will be faster. It consumes storage and must be maintained when indexed values are inserted, changed, or removed. A query optimizer compares possible execution plans and chooses a plan using estimates of cost and data distribution. Estimates can be inaccurate when statistics are outdated.

Transactions

A transaction is a group of database operations treated as one logical unit. Atomicity means that all its changes are committed or none are. Consistency means that a transaction preserves declared integrity constraints. Isolation governs how concurrent transactions interact. Durability means that committed changes survive the failures covered by the database's guarantees. Consider transferring money between accounts: reducing one balance and increasing the other must be handled together. If the second operation fails, the first should not remain as a completed transfer. Isolation levels trade stronger guarantees against possible concurrency costs; not every isolation level prevents all anomalies.

Normalization and recovery

Normalization organizes tables to reduce harmful redundancy and update anomalies. Functional dependencies describe how one set of attributes determines another. Decomposition must preserve the information required by the application, and designers consider whether constraints remain easy to enforce. Denormalization can improve selected read workloads but introduces additional consistency work. A backup is a recoverable copy of data, while a transaction log records changes used for recovery. Backups should be tested by restoration rather than assumed to be usable. Access control grants only the permissions needed for a role. Students may read a course catalog while staff manage enrollment records. Encryption, backups, and authorization solve different problems; none is a substitute for the others.'''

OS = '''Processes and scheduling

An operating system manages hardware resources and provides services to programs. A process is a program in execution together with its execution state and resources. A thread is an execution path within a process. Threads in one process usually share its address space, so they can communicate efficiently but require coordination when changing shared data. A context switch saves one execution state and restores another. Context switching has a cost; it is not useful computation performed by the application.

The scheduler selects a runnable task for CPU execution. First-come, first-served scheduling considers arrival order. Round-robin scheduling gives runnable tasks a time quantum in turn. A very small quantum can increase context-switch overhead, while a very large quantum can reduce responsiveness. Scheduling objectives include throughput, turnaround time, waiting time, and response time. Improving one objective can worsen another. Priority scheduling can starve low-priority work unless the policy includes a mechanism such as aging.

Memory management

Virtual memory gives a process a virtual address space that is mapped to physical memory. Paging divides virtual memory into pages and physical memory into frames. A page table records mappings and access permissions. The translation lookaside buffer caches recent address translations. A page fault occurs when an access cannot be completed using the current page mapping and needs operating-system handling. It does not always mean that the program has made an illegal access. Excessive paging can lead to thrashing, where moving pages consumes much of the available time.

Synchronization and deadlock

A race condition occurs when a result depends on an unintended ordering of concurrent operations. A mutex protects a critical section so that only one participant holds the lock at a time. Deadlock is a condition in which tasks wait indefinitely for resources held by one another. The classic necessary conditions are mutual exclusion, hold and wait, no preemption, and circular wait. Preventing at least one condition prevents this form of deadlock, but the chosen policy can reduce concurrency. Acquiring locks in a consistent global order is one way to prevent circular wait.

Files and input/output

A file system organizes persistent data and metadata. Directories map names to stored objects. File permissions control operations such as reading and writing. Buffering temporarily stores data to manage differences in transfer rates. Caching retains copies to reduce repeated access costs, but cached data must remain consistent with the underlying state. A system call is an interface through which a program requests a privileged operating-system service. User mode restricts direct access to sensitive hardware operations; kernel mode permits the operating system to perform them. This separation reduces the damage that an ordinary application can cause.'''

DS = '''Data structures

An array stores indexed elements and supports direct access by position. Inserting into the middle of a fixed contiguous representation can require moving later elements. A linked list stores nodes connected by references. It can make some insertions inexpensive when the relevant node is already known, but finding that node can require traversal. Choosing between these structures depends on the operations and workload rather than on a universal ranking.

A stack follows last-in, first-out order. A queue follows first-in, first-out order. Stacks support function-call management and iterative depth-first traversal. Queues support breadth-first traversal and work scheduling. A hash table maps keys to positions using a hash function. Collisions occur when different keys map to the same position. Collision handling and resizing affect performance. Average-case constant-time lookup depends on assumptions about hashing and load; it does not eliminate worst-case behavior.

A graph contains vertices and edges. In a directed graph, edges have an orientation. Breadth-first search finds shortest paths by number of edges in an unweighted graph. Dijkstra's algorithm requires nonnegative edge weights. Applying it without that condition can give incorrect results. An adjacency list is often suitable for sparse graphs, while an adjacency matrix can be useful for constant-time edge existence checks at the cost of quadratic storage.

Binary search procedure
1. Start with the complete sorted interval.
2. Compare the target with the middle element.
3. Discard the half that cannot contain the target.
4. Repeat until the target is found or the interval is empty.

An invariant is a property maintained through an algorithm's execution. For binary search, the candidate interval must continue to contain every location at which the target could occur. Careful boundary updates prevent infinite loops and skipped elements. Tests should include an empty list, a single element, missing targets, and targets at both ends.'''

ML = '''Machine learning evaluation

Supervised learning uses examples with target labels to learn a mapping from inputs to outputs. Classification predicts a category, while regression predicts a numerical value. Training data is used to fit model parameters. Validation data helps select settings, and test data is reserved for final evaluation. Repeatedly adjusting a model based on the test set turns that set into part of the development process and makes the final score less trustworthy.

Overfitting occurs when a model fits details of training data that do not generalize. Regularization, simpler models, additional representative data, and early stopping can reduce overfitting. Underfitting occurs when the model does not capture important patterns even in the training data. Data leakage occurs when information unavailable at prediction time enters model development. For example, computing preprocessing statistics across both training and test data can leak information. Preprocessing should be fitted on the training split and then applied consistently to other splits.

Accuracy measures the fraction of correct predictions but can be misleading for imbalanced classes. Precision measures how many predicted positives are actually positive. Recall measures how many actual positives were found. A confusion matrix records true positives, false positives, true negatives, and false negatives. Evaluation should reflect the cost of errors in the intended application. A medical screening task and a spam filter can assign very different costs to false negatives and false positives.

Precision = TP / (TP + FP)
Recall = TP / (TP + FN)

Cross-validation estimates performance across multiple data splits. For time-dependent observations, splitting must respect chronology to avoid learning from the future. Correlation does not by itself establish causation. A model can predict well using a correlated feature without that feature being the cause of the outcome. Deployment also requires monitoring distribution changes and evaluating performance on relevant subgroups. A high aggregate score does not prove that every group receives equally reliable predictions.'''

FIXTURES = {'cs_paragraph': CS, 'dbms_page': DBMS, 'os_section': OS,
            'multi_page_ds_ml': '\n\n'.join([CS, DBMS, OS, DS, ML])}


def main():
    output = Path('benchmark_results')
    output.mkdir(exist_ok=True)
    process = psutil.Process()
    samples = []
    stopped = threading.Event()
    def sample():
        while not stopped.wait(.1):
            samples.append(process.memory_info().rss)
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    report = {'model': 'google/flan-t5-base', 'threads': 4, 'baseline_rss_mb': process.memory_info().rss/1024**2,
              'cases': [], 'offline_network_blocked': True}
    try:
        # Even accidental network attempts fail immediately during the benchmark.
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden during local inference')):
            for name, source in FIXTURES.items():
                for mode in ('short', 'detailed', 'key_points', 'exam_notes', 'simple'):
                    started = perf_counter()
                    first_sample = len(samples)
                    case = {'case': name, 'mode': mode, 'words': len(source.split())}
                    try:
                        result = summarization_service.summarize(source, name, mode)
                        case.update(result)
                        case['success'] = True
                    except Exception as exc:
                        case.update(success=False, error=getattr(exc, 'detail', type(exc).__name__))
                    case['wall_seconds'] = round(perf_counter()-started, 3)
                    case['peak_sampled_rss_mb'] = round(max(samples[first_sample:] or [process.memory_info().rss])/1024**2, 1)
                    report['cases'].append(case)
                    report['load_count'] = summarization_service.load_count
                    report['model_load_seconds'] = round(summarization_service.load_seconds, 3)
                    report['peak_process_rss_mb'] = round(max(samples or [process.memory_info().rss])/1024**2, 1)
                    (output/'local_summary_benchmark.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
                    print({k:case[k] for k in ('case','mode','success','wall_seconds','peak_sampled_rss_mb')}, flush=True)
    finally:
        stopped.set()
        thread.join(timeout=1)
    print({'model_load_seconds':report['model_load_seconds'], 'model_load_count':report['load_count'], 'peak_rss_mb':report['peak_process_rss_mb']}, flush=True)


if __name__ == '__main__':
    main()
