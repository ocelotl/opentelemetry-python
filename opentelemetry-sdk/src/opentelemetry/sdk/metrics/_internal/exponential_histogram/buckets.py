# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from abc import ABC, abstractmethod


class Backing(ABC):
    @abstractmethod
    def size(self) -> int:
        """
        Returns the physical size of
        """

    @abstractmethod
    def grow(
        self, new_size: int, old_positive_limit: int, new_positive_limit: int
    ) -> None:
        """
        Grows the backing array into a new size and copies old entries into
        their correct new positions.
        """

    @abstractmethod
    def reverse(self, start: int, end: int) -> None:
        """
        Reverses the items in the backing array from [start, end).
        """

    @abstractmethod
    def empty_bucket(self, src: int) -> int:
        """
        Empties the count from a bucket for moving into another one
        """

    @abstractmethod
    def increment(self, bucket_index: int, increment: int) -> bool:
        """
        Increments a bucket by increment
        """

    @abstractmethod
    def count_at(self, pos: int) -> int:
        """
        Returns the count at a specific bucket.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Resets all buckets to zero count
        """


class VariableWidthBacking(Backing):
    def __init__(self):

        self._counts = [0]

    def size(self) -> int:
        """
        Returns the physical size of the backing array, which is
        >= buckets.Len() the number allocated.
        """
        return len(self._counts)

    def grow(
        self, new_size: int, old_positive_limit: int, new_positive_limit: int
    ) -> None:
        """
        Grows the backing array into a new size and copies old entries into
        their correct new positions.
        """
        tmp = [0] * new_size
        tmp[new_positive_limit:] = self._counts[old_positive_limit:]
        tmp[0:old_positive_limit] = self._counts[0:old_positive_limit]
        self._counts = tmp

    def reverse(self, start: int, end: int) -> None:
        """
        Reverses the items in the backing array from [start, end[.
        """

        for index, value in enumerate(reversed(self._counts[start:end])):
            self._counts[index + start] = value

    def empty_bucket(self, src: int) -> int:
        """
        Empties the count from a bucket for moving into another one
        returns the count from that bucket before it was set to zero.
        """

        temp = self._counts[src]
        self._counts[src] = 0
        return temp

    def increment(self, bucket_index: int, increment: int) -> None:
        """
        Increments a bucket by increment
        """

        self._counts[bucket_index] += increment

    def count_at(self, pos: int) -> int:
        """
        Returns the count at a specific bucket.
        """

        return self._counts[pos]

    def reset(self) -> None:
        """
        Resets all buckets to zero count
        """

        self._counts = [0] * len(self._counts)


class Buckets:
    def __init__(self):
        self._backing = VariableWidthBacking()

        # The term "index" refers to the number of the
        # histogram bucket used to determine its boundaries.
        # The lower-boundary of a bucket is determined by
        # formula base**index and the upper-boundary of a
        # bucket is base**(index+1).  Index values are signed
        # to account for values less than or equal to 1.

        # Index of the 0th position in the backing array: backing[0] is the
        # count in the bucket with index self._index_base.
        self._index_base = 0

        # indexStart is the smallest index value represented in the backing
        # array.
        self._index_start = 0

        # indexEnd is the largest index value represented in the backing array.
        self._index_end = 0

    def offset(self) -> int:
        return self._index_start

    def len(self) -> int:
        if self._backing.size() == 0:
            return 0

        if self._index_end == self._index_start and self.at(0) == 0:
            return 0

        return self._index_end - self._index_start + 1

    # pylint: disable=invalid-name
    def at(self, position: int) -> int:
        bias = self._index_base - self._index_start

        if position < bias:
            position += self._backing.size()

        position -= bias

        return self._backing.count_at(position)

    def clear(self) -> None:

        self._index_base = 0
        self._index_start = 0
        self._index_end = 0

        self._backing.reset()

    # pylint: disable=invalid-name
    def downscale(self, by: int) -> None:
        """
        Rotates, then collapses 2**`by`-to-1 buckets.
        """

        bias = self._index_base - self._index_start

        if bias != 0:

            self._index_base = self._index_start

            self._backing.reverse(0, self._backing.size())
            self._backing.reverse(0, bias)
            self._backing.reverse(bias, self._backing.size())

        size = 1 + self._index_end - self._index_start
        each = 1 << by
        inpos = 0
        outpos = 0

        pos = self._index_start

        while pos <= self._index_end:
            mod = pos % each
            if mod < 0:
                mod += each

            index = mod

            while index < each and inpos < size:

                if outpos != inpos:
                    self.increment_bucket(
                        outpos, self._backing.empty_bucket(inpos)
                    )

                inpos += 1
                pos += 1
                index += 1

            outpos += 1

        self._index_start >>= by
        self._index_end >>= by
        self._index_base = self._index_start

    def increment_bucket(self, bucket_index: int, incr: int):
        self._backing.increment(bucket_index, incr)
