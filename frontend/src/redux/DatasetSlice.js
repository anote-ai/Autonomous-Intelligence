import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

// Mock async thunk for loading datasets
export const loadDatasets = createAsyncThunk(
  'datasets/loadDatasets',
  async () => {
    // Mock dataset loading - in a real app this would be an API call
    return [
      { id: 1, name: 'flores_spanish_translation', type: 'translation' },
      { id: 2, name: 'financebench', type: 'chatbot' },
      { id: 3, name: 'emotion', type: 'classification' }
    ];
  }
);

const datasetsSlice = createSlice({
  name: 'datasets',
  initialState: {
    datasets: [],
    loading: false,
    error: null
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(loadDatasets.pending, (state) => {
        state.loading = true;
      })
      .addCase(loadDatasets.fulfilled, (state, action) => {
        state.loading = false;
        state.datasets = action.payload;
      })
      .addCase(loadDatasets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  }
});

// Selector hook
export const useDatasets = () => {
  // Mock hook - in a real app this would use useSelector
  return [];
};

export default datasetsSlice.reducer; 