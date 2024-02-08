#!/usr/bin/python3

import glob
import os
import sys
import time
import pandas as pd
import turbopuffer as tpuf
import traceback
import threading
from queue import Queue, Full

NUM_THREADS = 4
START_OFFSET = 0

def read_docs_to_queue(queue, parquet_files, exiting):
    try:
        file_offset = 0
        for parquet_file in parquet_files:
            while queue.full() and not exiting.is_set():
                time.sleep(1)
            if exiting.is_set():
                return
            # Add any attribute columns to include after 'emb'
            df = pd.read_parquet(parquet_file, columns=['emb']).rename(columns={'emb': 'vector'})
            if 'id' not in df.keys():
                df['id'] = range(file_offset, file_offset+len(df))
            if file_offset >= START_OFFSET:
                while not exiting.is_set():
                    try:
                        queue.put(df, timeout=1)
                        break
                    except Full:
                        pass
                print(f'Loaded {parquet_file}, file_offset from {file_offset} to {file_offset + len(df)}')
            else:
                print(f'Skipped {parquet_file}, file_offset from {file_offset} to {file_offset + len(df)}')
            file_offset += len(df)
    except Exception:
        print('Failed to read batch:')
        traceback.print_exc()
    for _ in range(0, NUM_THREADS):
        queue.put(None)  # Signal the end of the documents


def upsert_docs_from_queue(input_queue, dataset_name, exiting):
    ns = tpuf.Namespace(dataset_name)

    batch = input_queue.get()
    while batch is not None and not exiting.is_set():
        try:
            ns.upsert(batch)
            print(f"Completed {batch['id'][0]}..{batch['id'][batch.shape[0]-1]}")
        except Exception:
            print(f"Failed to upsert batch: {batch['id'][0]}..{batch['id'][batch.shape[0]-1]}")
            traceback.print_exc()
        batch = input_queue.get()


def main(dataset_name, input_path):
    input_glob = os.path.join(input_path, "*.parquet")
    parquet_files = glob.glob(input_glob)

    if len(parquet_files) == 0:
        print(f"No .parquet files found in: {input_glob}")
        sys.exit(1)

    sorted_files = sorted(sorted(parquet_files), key=len)

    ns = tpuf.Namespace(dataset_name)
    if ns.exists():
        print(f'The namespace "{ns.name}" already exists!')
        existing_dims = ns.dimensions()
        print(f'Vectors: {ns.approx_count()}, dimensions: {existing_dims}')
        response = input('Delete namespace? [y/N]: ')
        if response == 'y':
            ns.delete_all()
        else:
            print('Cancelled')
            sys.exit(1)

    exiting = threading.Event()
    doc_queue = Queue(NUM_THREADS)
    read_thread = threading.Thread(target=read_docs_to_queue, args=(doc_queue, sorted_files, exiting))
    upsert_threads = []

    start_time = time.monotonic()

    try:
        read_thread.start()

        for _ in range(NUM_THREADS):
            upsert_thread = threading.Thread(target=upsert_docs_from_queue, args=(doc_queue, dataset_name, exiting))
            upsert_threads.append(upsert_thread)
            upsert_thread.start()

        read_thread.join()

        for upsert_thread in upsert_threads:
            upsert_thread.join()
    except KeyboardInterrupt:
        exiting.set()
        sys.exit(1)
    finally:
        print('DONE!')
        print('Took:', (time.monotonic() - start_time), 'seconds')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <dataset_name> <input_folder>\n"
              "    Default TURBOPUFFER_API_KEY will be used from environment.")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
