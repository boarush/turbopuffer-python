import turbopuffer as tpuf

def test_vector_endpoints():
    namespace = tpuf.Namespace('hello_world')
    print(namespace)

    # Test upsert dict data
    namespace.upsert({
        "ids": [0, 1, 2, 3],
        "vectors": [[0.0, 0.0], [0.1, 0.1], [0.2, 0.2], [0.3, 0.3]],
        "attributes": {"key1": ["zero", "one", "two", "three"], "key2": [" ", "a", "b", "c"]}
    })

    # Test upsert typed column data
    namespace.upsert(tpuf.VectorColumns(
        ids=[4, 5, 6],
        vectors=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]],
        attributes={"key1": ["one", "two", "three"], "key2": ["a", "b", "c"]},
    ))

    # Test upsert delete single row
    namespace.upsert(tpuf.VectorRow(id=2))

    # Test upsert single row dict
    namespace.upsert({'id': 2})

    # Test upsert typed row data
    namespace.upsert([
        tpuf.VectorRow(id=2, vector=[2, 2]),
        tpuf.VectorRow(id=7, vector=[0.7, 0.7], attributes={'hello': 'world'}),
    ])

    # Test query with dict
    vector_set = namespace.query({
        'vector': [0.8, 0.7],
        'distance_metric': 'euclidean_squared',
        'include_vectors': True,
        'include_attributes': ['hello'],
    })
    for i, vector in enumerate(vector_set):
        print(f'Query {i}: ', vector)

    # Test query with typed query
    vector_set = namespace.query(tpuf.VectorQuery(
        vector=[0.8, 0.7],
        distance_metric='euclidean_squared',
        include_vectors=True,
        include_attributes=['hello'],
    ))
    for i, vector in enumerate(vector_set):
        print(f'Query {i}: ', vector)

    vector_set = namespace.vectors()
    for i, vector in enumerate(vector_set):
        print(f'Export {i}: ', vector)

    namespace.delete_all()
