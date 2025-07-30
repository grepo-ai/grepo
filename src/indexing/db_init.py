from pymilvus import MilvusClient, DataType, Function, FunctionType


class BM25db:
    def __init__(self):
        self._db_client = MilvusClient("./grepo.db")
        self.schema = self.create_schema()
        self.collection = self.create_collection()

    def create_schema(self):
        self.schema = self._client.create_schema()

        self.schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
        )
        self.schema.add_field(
            field_name="code_block",
            datatype=DataType.VARCHAR,
            max_length=8192,
            enable_analyzer=True,
        )
        self.schema.add_field(
            field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR
        )
        self.schema.add_field(field_name="meta", datatype=DataType.JSON, nullable=True)

        # Define BM25 function for converting text to sparse representation
        bm25_function = Function(
            name="code_bm25",
            input_field_names=["code_block"],
            output_field_names=["sparse"],
            function_type=FunctionType.BM25,
        )

        self.schema.add_function(bm25_function)

        return self.schema

    def create_collection(self):
        # Setup db index
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75,
            },
        )

        # Create a collection
        self._client.create_collection(
            collection_name="grepo_collection",
            schema=self.schema,
            index_params=index_params,
        )
