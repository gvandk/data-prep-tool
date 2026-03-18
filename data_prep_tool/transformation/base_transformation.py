from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper

class BaseTransformation:
    """Base class for all transformations."""
    def apply(self, df_wrapper: DataFrameWrapper) -> DataFrameWrapper:
        """Apply transformation to DataFrameWrapper."""
        raise NotImplementedError()
    
    def undo(self, df_wrapper: DataFrameWrapper) -> DataFrameWrapper:
        """Undo transformation on DataFrameWrapper."""
        raise NotImplementedError()