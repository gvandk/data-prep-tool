from core.dataframe_wrapper import DataFrameWrapper

class BaseTransformation:
    def apply(self, df_wrapper: DataFrameWrapper) -> DataFrameWrapper:
        """Apply transformation to DataFrameWrapper."""
        raise NotImplementedError()
    
    def undo(self, df_wrapper: DataFrameWrapper) -> DataFrameWrapper:
        """Undo transformation on DataFrameWrapper."""
        raise NotImplementedError()
    
    def to_script(self) -> str:
        """Converert transformation to script."""
        raise NotImplementedError()