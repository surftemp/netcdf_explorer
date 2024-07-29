import numpy as np
import gzip


class DataEncoder:

    @staticmethod
    def encode(arr, path):
        with open(path,"wb") as f:
            height, width = arr.shape
            dim_arr = np.array([height,width],dtype="<i4")
            f.write(gzip.compress(dim_arr.tobytes()+arr.astype("<f4").tobytes()))