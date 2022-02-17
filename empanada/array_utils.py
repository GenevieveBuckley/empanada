import math
import numpy as np
import numba

def take(array, indices, axis=0):
    indices = tuple([
        slice(None) if n != axis else indices
        for n in range(array.ndim)
    ])

    return array[indices]

def put(array, indices, value, axis=0):
    indices = tuple([
        slice(None) if n != axis else indices
        for n in range(array.ndim)
    ])

    # modify the array inplace
    array[indices] = value

def box_area(boxes):
    """
    Computes the area/volume of a set of boxes.

    Arguments:
    ----------
    boxes: Array of size (n, 4) or (n, 6) where bounding box
    is defined as (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    Returns:
    --------
    areas: Array of (n,) of each box area/volume.

    """

    ndim = boxes.shape[1] // 2

    dims = []
    for i in range(ndim):
        dims.append(boxes[:, i+ndim] - boxes[:, i])

    return math.prod(dims)


def box_intersection(boxes1, boxes2=None):
    """
    Computes the pairwise intersection area/volume between two arrays of
    bounding boxes.

    Arguments:
    ----------
    boxes1: Array of size (n, 4) or (n, 6) where bounding box
    is defined as (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    boxes2: Array of size (m, 4) or (m, 6) where bounding box
    is defined as (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).
    If None, then pairwise intersections are calculated between
    all pairs of boxes in boxes1. Default, None.

    Returns:
    --------
    intersections: Array of (n, m) defining pairwise area/volume
    intersection between boxes.

    """

    # do pairwise box iou if no boxes2
    if boxes2 is None:
        boxes2 = boxes1

    ndim = boxes1.shape[1] // 2

    box_coords1 = np.split(boxes1, ndim*2, axis=1)
    box_coords2 = np.split(boxes2, ndim*2, axis=1)

    intersect_dims = []
    for i in range(ndim):
        pairs_max_low = np.maximum(box_coords1[i], np.transpose(box_coords2[i]))
        pairs_min_high = np.minimum(box_coords1[i+ndim], np.transpose(box_coords2[i+ndim]))

        intersect_dims.append(
            np.maximum(np.zeros(pairs_max_low.shape), pairs_min_high - pairs_max_low)
        )

    return np.prod(intersect_dims, axis=0)

def merge_boxes(box1, box2):
    """
    Merges two bounding boxes into 1 box that encloses both.

    Arguments:
    ----------
    box1: Bounding box tuple of (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    box2: Bounding box tuple of (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    Returns:
    --------
    merged_box: Bounding box tuple of (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).
    Defines the box that completely encloses box1 and box2.

    """
    n = len(box1)
    ndim = n // 2

    merged_box = []
    for i in range(n):
        if i < ndim:
            coord = min(box1[i], box2[i])
        else:
            coord = max(box1[i], box2[i])

        merged_box.append(coord)

    return tuple(merged_box)

def box_iou(boxes1, boxes2=None, return_intersection=False):
    """
    Calculates the pairwise intersection-over-union between sets of boxes.

    Arguments:
    ----------
    boxes1: Array of size (n, 4) or (n, 6) where bounding box
    is defined as (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    boxes2: Array of size (m, 4) or (m, 6) where bounding box
    is defined as (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).
    If None, then pairwise IoUs are calculated between
    all pairs of boxes in boxes1. Default, None.

    Returns:
    --------
    ious: Array of (n, m) defining pairwise IoUs between boxes.

    """
    # do pairwise box iou if no boxes2
    if boxes2 is None:
        boxes2 = boxes1

    intersect = box_intersection(boxes1, boxes2)
    area1 = box_area(boxes1)
    area2 = box_area(boxes2)

    # union is a matrix of same size as intersect
    union = area1[:, None] + area2[None, :] - intersect
    iou = intersect / union
    if return_intersection:
        return iou, intersect
    else:
        return iou

def rle_encode(indices):
    """
    Run length encodes an array of 1d indices.

    Arguments:
    ----------
    indices: An array of (n,) indices to run length encode.

    Returns:
    --------
    starts: Array of (l,) starting indices.

    runs: Array of (l,) run lengths.

    """
    # where indices are not contiguous
    changes = np.where(indices[1:] != indices[:-1] + 1)[0] + 1

    # add first and last indices
    changes = np.insert(changes, 0, [0], axis=0)
    changes = np.append(changes, [len(indices)], axis=0)

    # measure distance between changes (i.e. run length)
    runs = changes[1:] - changes[:-1]

    # remove last change
    changes = changes[:-1]

    assert(len(changes) == len(runs))

    return indices[changes], runs

def rle_decode(starts, runs):
    """
    Decodes run length encoding arrays to an array of indices.

    Arguments:
    --------
    starts: Array of (l,) starting indices.

    runs: Array of (l,) run lengths.

    Returns:
    --------
    indices: An array of (n,) decoded indices.

    """
    ends = starts + runs
    indices = np.concatenate(
        [np.arange(s, e) for s,e in zip(starts, ends)]
    )
    return indices

def rle_to_string(starts, runs):
    """
    Converts run length encoding to a string.

    Arguments:
    --------
    starts: Array of (l,) starting indices.

    runs: Array of (l,) run lengths.

    Returns:
    --------
    rle_string: String representation of a run length encoding.
    Format is "starts[0] runs[0] starts[1] runs[1] ... starts[n] runs[n]"

    """

    return ' '.join([f'{i} {r}' for i,r in zip(starts, runs)])

def string_to_rle(encoding):
    """
    Converts run length encoding string to start and run arrays.

    Arguments:
    --------
    rle_string: String representation of a run length encoding.
    Format is "starts[0] runs[0] starts[1] runs[1] ... starts[n] runs[n]"

    Returns:
    --------
    starts: Array of (l,) starting indices.

    runs: Array of (l,) run lengths.

    """
    encoding = np.array([int(i) for i in encoding.split(' ')])
    starts, runs = encoding[::2], encoding[1::2]
    return starts, runs

def crop_and_binarize(mask, box, label):
    """
    Crop a mask from a bounding box and binarize the cropped mask
    where it's equal to the given label value.

    Arguments:
    ----------
    mask: Array of (h, w) or (d, h, w) defining an image.

    box: Bounding box tuple of (y1, x1, y2, x2) or (z1, y1, x1, z2, y2, x2).

    label: Label value to binarize within cropped mask.

    Returns:
    --------
    binary_cropped_mask: Boolean array of (h', w') or (d', h', w').

    """
    ndim = len(box) // 2
    slices = tuple([slice(box[i], box[i+ndim]) for i in range(ndim)])

    return mask[slices] == label

def mask_iou(mask1, mask2, return_intersection=False):
    """
    Calculates IoU score between two binary masks.

    Arguments:
    ---------
    mask1: Boolean array of (h, w) or (d, h, w) defining an image.

    mask2: Boolean array of (h, w) or (d, h, w) defining an image.

    Returns:
    --------
    iou_score: Float IoU score.

    """
    intersection = np.count_nonzero(np.logical_and(mask1, mask2))
    union = np.count_nonzero(np.logical_or(mask1, mask2))
    iou = intersection / union
    
    if return_intersection:
        return iou, intersect
    else:
        return iou

def mask_ioa(mask1, mask2):
    """
    Calculates IoA score between two binary masks.
    The object area is derived from mask2.

    Arguments:
    ---------
    mask1: Boolean array of (h, w) or (d, h, w) defining an image.

    mask2: Boolean array of (h, w) or (d, h, w) defining an image.

    Returns:
    --------
    ioa_score: Float IoA score.

    """
    intersection = np.count_nonzero(np.logical_and(mask1, mask2))
    area = np.count_nonzero(mask2)
    return intersection / area

@numba.jit(nopython=True)
def intersection_from_ranges(merged_runs, changes):
    """
    Computes intersection from run ranges.

    Arguments:
    ----------
    merged_runs: Integer array of (n, 2) where each element is a range of [start, end].

    changes: Boolean array of (n,). True where the current range is from a different
    source run length encoding than the next range.

    Returns:
    --------
    intersection: Integer, number of pixels/voxels that overlap in merged_runs.

    """
    total_inter = 0

    check_run = None
    for is_change, run1, run2 in zip(changes, merged_runs[:-1], merged_runs[1:]):
        if is_change:
            check_run = run1
        elif check_run is None:
            continue

        if check_run[1] < run2[0]:
            continue

        total_inter += min(check_run[1], run2[1]) - max(check_run[0], run2[0])

    return total_inter

def rle_iou(starts_a, runs_a, starts_b, runs_b, return_intersection=False):
    """
    Calculates the IoU between two run length encodings.

    Arguments:
    ----------
    starts_a: Array of (n,) where each element is the starting index of a run.
    
    runs_a: Array of (n,) where each element is the run length of a run.
    
    starts_b: Array of (m,) where each element is the starting index of a run.
    
    runs_b: Array of (m, ) where each element is the run length of a run.

    return_intersection: Integer, total number of overlapping pixels/voxels.

    Returns:
    --------
    iou: Float, the intersection-over-union score.

    intersection: If return_intersection is True, returns intersection.

    """
    # convert from runs to ends
    ranges_a = np.stack([starts_a, starts_a + runs_a], axis=1)
    ranges_b = np.stack([starts_b, starts_b + runs_b], axis=1)

    # merge and sort the ranges from two rles
    merged_runs = np.concatenate([ranges_a, ranges_b], axis=0)
    merged_ids = np.concatenate(
        [np.repeat([0], len(ranges_a)), np.repeat([1], len(ranges_b))]
    )
    sort_indices = np.argsort(merged_runs, axis=0, kind='stable')[:, 0]

    # find where the rle ids change between merged runs
    merged_runs = merged_runs[sort_indices]
    merged_ids = merged_ids[sort_indices]
    changes = merged_ids[:-1] != merged_ids[1:]

    # calculate intersection and divide by union
    intersection = intersection_from_ranges(merged_runs, changes)
    union = runs_a.sum() + runs_b.sum() - intersection
    
    if return_intersection:
        return intersection / union, intersection
    else:
        return intersection / union
    
def rle_ioa(starts_a, runs_a, starts_b, runs_b, return_intersection=False):
    """
    Calculates the IoU between two run length encodings.

    Arguments:
    ----------
    starts_a: Array of (n,) where each element is the starting index of a run.
    
    runs_a: Array of (n,) where each element is the run length of a run.
    
    starts_b: Array of (m,) where each element is the starting index of a run.
    
    runs_b: Array of (m, ) where each element is the run length of a run.

    return_intersection: Integer, total number of overlapping pixels/voxels.

    Returns:
    --------
    iou: Float, the intersection-over-union score.

    intersection: If return_intersection is True, returns intersection.

    """
    # convert from runs to ends
    ranges_a = np.stack([starts_a, starts_a + runs_a], axis=1)
    ranges_b = np.stack([starts_b, starts_b + runs_b], axis=1)

    # merge and sort the ranges from two rles
    merged_runs = np.concatenate([ranges_a, ranges_b], axis=0)
    merged_ids = np.concatenate(
        [np.repeat([0], len(ranges_a)), np.repeat([1], len(ranges_b))]
    )
    sort_indices = np.argsort(merged_runs, axis=0, kind='stable')[:, 0]

    # find where the rle ids change between merged runs
    merged_runs = merged_runs[sort_indices]
    merged_ids = merged_ids[sort_indices]
    changes = merged_ids[:-1] != merged_ids[1:]

    # calculate intersection and divide by union
    intersection = intersection_from_ranges(merged_runs, changes)
    area = runs_b.sum()
    
    if return_intersection:
        return intersection / area, intersection
    else:
        return intersection / area

@numba.jit(nopython=True)
def split_range_by_votes(running_range, num_votes, vote_thr=2):
    """
    Splits a range into two new ranges based on the votes for each index.

    Arguments:
    ----------
    running_range: List of 2. First element is the run start and second element is run end.

    num_votes: List of n. Each element is the number of votes for a particular index
    within the range(start, end).

    vote_thr: Minimum number of votes for an index to be kept in the running range.

    Returns:
    --------
    split_voted_ranges: List of new ranges with indices that had too few votes removed.

    """
    # the running range may be split at places with
    # too few votes to cross the vote_thr
    split_voted_ranges = []
    s, e = None, None
    for ix in range(len(num_votes)):
        n = num_votes[ix]
        if n >= vote_thr:
            if s is None:
                s = running_range[0] + ix
            else:
                e = running_range[0] + ix + 1
        elif s is not None:
            # needed in case run of just 1
            e = s + 1 if e is None else e
            # append and reset
            split_voted_ranges.append([s, e])
            s = None
            e = None

    # finish off the last run
    if s is not None:
        e = s + 1 if e is None else e
        split_voted_ranges.append([s, e])

    return split_voted_ranges

@numba.jit(nopython=True)
def extend_range(range1, range2, num_votes):
    """

    """
    # difference between starts is location
    # in num_votes1 to start updating
    first_idx = range2[0] - range1[0]
    last_idx = len(num_votes)
    end_offset = range2[1] - range1[1]

    if end_offset > 0:
        # if range2 extends past range1
        # then add more votes to list
        # and update range1
        extension = [1 for _ in range(end_offset)]
        range1[1] = range2[1]
        num_votes.extend(extension)
    elif end_offset < 0:
        # adjust last_index because range2 doesn't
        # extend as far as range1
        last_idx += end_offset

    # increate vote totals
    for i in range(first_idx, last_idx):
        num_votes[i] += 1

    return range1, num_votes

@numba.jit(nopython=True)
def rle_voting(ranges, vote_thr=2):
    # ranges that past the vote_thr
    voted_ranges = []

    # initialize starting range and votes
    # for each index in the range
    running_range = None
    num_votes = None

    for range1,range2 in zip(ranges[:-1], ranges[1:]):
        if running_range is None:
            running_range = range1
            # all indices get 1 vote from range1
            num_votes = [1 for _ in range(range1[1] - range1[0])]

        # if starting index in range 2 is greater
        # than the end index of the running range there
        # is no overlap and we start tracking a new range
        if running_range[1] < range2[0]:
            # add ranges and reset
            voted_ranges.extend(
                split_range_by_votes(running_range, num_votes, vote_thr)
            )
            running_range = None
            num_votes = None
        else:
            # extend the running range and accumulate votes
            running_range, num_votes = extend_range(
                running_range, range2, num_votes
            )

    # if range was still going at the end
    # of the loop then finish processing it
    if running_range is not None:
        voted_ranges.extend(
            split_range_by_votes(running_range, num_votes, vote_thr)
        )

    return voted_ranges

@numba.jit(nopython=True)
def join_ranges(ranges):
    joined = []
    running_range = None
    for range1,range2 in zip(ranges[:-1], ranges[1:]):
        if running_range is None:
            running_range = range1

        if running_range[1] >= range2[0]:
            running_range[1] = max(running_range[1], range2[1])
        else:
            joined.append(running_range)
            running_range = None

    if running_range is not None:
        joined.append(running_range)
    else:
        joined.append(range2)

    return joined

def merge_rles(starts_a, runs_a, starts_b=None, runs_b=None):
    # convert from runs to ranges
    if starts_b is not None and runs_b is not None:
        ranges_a = np.stack([starts_a, starts_a + runs_a], axis=1)
        ranges_b = np.stack([starts_b, starts_b + runs_b], axis=1)
        merged_ranges = np.concatenate([ranges_a, ranges_b], axis=0)
    else:
        merged_ranges = np.stack([starts_a, starts_a + runs_a], axis=1)
    
    sort_indices = np.argsort(merged_ranges[:, 0], axis=0, kind='stable')
    merged_ranges = merged_ranges[sort_indices]

    joined = np.array(join_ranges(merged_ranges))

    # convert from ranges to runs
    return joined[:, 0], joined[:, 1] - joined[:, 0]
