# Manual review packets

30 test records x 2 docstrings, seed 2026.

## 1. quantopian/zipline :: Factor.winsorize  (`3cdb66d5ceb5`)

Code diff:
```diff
-                   limits,
+                   min_percentile,
-                   inclusive=(True, True),
+                   max_percentile,
+         if not 0.0 <= min_percentile < max_percentile <= 1.0:
+             raise BadPercentileBounds(
+                 min_percentile=min_percentile,
+                 max_percentile=max_percentile,
+                 upper_bound=1.0,
+             )
-             transform_args=(limits, inclusive),
+             transform_args=(min_percentile, max_percentile),
```

### Docstring before commit -> **potential_drift**
```text
Construct a Factor returns a winsorized row for results. Winsorizing
        clips the input values to fixed percentiles. The (limits[0])th lowest
        values are set to the value at the (limits[0])th percentile. The values
        above the (limits[1])th percentiles are set to the value at the
        (limits[1])th percentile. This is useful when limiting the impact of
        extreme values.

        If ``mask`` is supplied, ignore values where ``mask`` returns False
        when computing row means and standard deviations, and output NaN
        anywhere the mask is False.

        If ``groupby`` is supplied, compute by partitioning each row based on
        the values produced by ``groupby``, winsorizing the partitioned arrays,
        and stitching the sub-results back together.

        Parameters
        ----------
        limits : None, tuple of float, optional
            A tuple of two values between 0 and 100 inclusive. This is the
            percentage to cut from each tail of the array. A value of None
            can be used to indicate an open limit.
        inclusive : a tuple of bool, optional
            A bool indicating whether the data on each side should be
            rounded(True) or truncated(False). A value of None can be used if
            one side is not being winsorized. Default is (False, False).
        mask : zipline.pipeline.Filter, optional
            A Filter defining values to ignore when winsorizing.
        groupby : zipline.pipeline.Classifier, optional
            A classifier defining partitions over which to winsorize.

        Returns
        -------
        winsorized : zipline.pipeline.Factor
            A Factor producing a winsorized version of self.

        Example
        -------

        price = USEquityPricing.close.latest
        columns={
            'PRICE': price,
            'WINSOR_1: price.winsorize(limits=25),
            'WINSOR_2': price.winsorize(limits=(50, None)),
            'WINSOR_3': price.winsorize(
                limits=25, inclusive=(False, False)
            ),
            'WINSOR_4': price.winsorize(limits=25, inclusive=(True, False)),
            'WINSOR_5': price.winsorize(limits=(20, 40)),
        }

        Given a pipeline with columns, defined above, the result for a
        given day could look like:

                'PRICE' 'WINSOR_1' 'WINSOR_2' 'WINSOR_3' 'WINSOR_4' 'WINSOR_5'
        Asset_1    1        2          4          3          2          2
        Asset_2    2        2          4          3          2          2
        Asset_3    3        3          4          3          3          2
        Asset_4    4        4          4          4          4          4
        Asset_5    5        5          5          4          4          4
        Asset_6    6        5          5          4          4          4

        See Also
        --------
        :func:`scipy.stats.mstats.winsorize`
        :meth:`pandas.DataFrame.groupby`
```
- Summary: The documentation describes parameter(s) `inclusive`, `limits` that the current code does not have.
- Evidence [rule_r1]: Documented but not in the signature: inclusive, limits | lines: def winsorize(self,
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: inclusive, limits | lines: - limits, / - inclusive=(True, True), / - transform_args=(limits, inclusive),
- Evidence [term_overlap]: Terms shared with the current code: groupby, percentile, mask, factor, row
- Signals: TF-IDF -0.116, encoder +0.123
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Update the parameter list: remove or rename `inclusive`, `limits` to match the signature.

### Docstring after commit -> **no_obvious_drift**
```text
Construct a Factor returns a winsorized row. Winsorizing changes values
        ranked less than the minimum percentile to to value at the minimum
        percentile. Similarly, values ranking above the maximum percentile will
        be changed to the value at the maximum percentile. This is useful
        when limiting the impact of extreme values.

        If ``mask`` is supplied, ignore values where ``mask`` returns False
        when computing row means and standard deviations, and output NaN
        anywhere the mask is False.

        If ``groupby`` is supplied, compute by partitioning each row based on
        the values produced by ``groupby``, winsorizing the partitioned arrays,
        and stitching the sub-results back together.

        Parameters
        ----------
        min_percentile: float, int
            Entries with values at or below this percentile will be replaced
            with the (len(inp) * min_percentile)th lowest value. If low values
            should not be clipped, use 0.
        max_percentile: float, int
            Entries with values at or above this percentile will be replaced
            with the (len(inp) * max_percentile)th lowest value. If high
            values should not be clipped, use 1.
        mask : zipline.pipeline.Filter, optional
            A Filter defining values to ignore when winsorizing.
        groupby : zipline.pipeline.Classifier, optional
            A classifier defining partitions over which to winsorize.

        Returns
        -------
        winsorized : zipline.pipeline.Factor
            A Factor producing a winsorized version of self.

        Example
        -------

        price = USEquityPricing.close.latest
        columns={
            'PRICE': price,
            'WINSOR_1: price.winsorize(
                min_percentile=0.25, max_percentile=0.75
            ),
            'WINSOR_2': price.winsorize(
                min_percentile=0.50, max_percentile=1.0
            ),
            'WINSOR_3': price.winsorize(
                min_percentile=0.0, max_percentile=0.5
            ),

        }

        Given a pipeline with columns, defined above, the result for a
        given day could look like:

                'PRICE' 'WINSOR_1' 'WINSOR_2' 'WINSOR_3'
        Asset_1    1        2          4          3
        Asset_2    2        2          4          3
        Asset_3    3        3          4          3
        Asset_4    4        4          4          4
        Asset_5    5        5          5          4
        Asset_6    6        5          5          4

        See Also
        --------
        :func:`scipy.stats.mstats.winsorize`
        :meth:`pandas.DataFrame.groupby`
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: percentile, groupby, min, mask, max
- Signals: TF-IDF +0.203, encoder +0.137
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 2. LmeSzinc/AzurLaneAutoScript :: Button.load_color  (`a0595217ed39`)

Code diff:
```diff
-         color = get_color(image, self.area)
+         self.color = get_color(image, self.area)
-         self.color = color
+         self.image = np.array(image.crop(self.area))
-         return color
+         return self.color
```

### Docstring before commit -> **potential_drift**
```text
Load color from the specific area of the given image.
        This method is irreversible, this would be only use in some special occasion.

        Args:
            image (PIL.Image.Image): Another screenshot.

        Returns:
            tuple: Color (r, g, b).
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: color, image, area, load
- Signals: TF-IDF -0.023, encoder -0.046
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **potential_drift**
```text
Load color from the specific area of the given image.
        This method is irreversible, this would be only use in some special occasion.

        Args:
            image: Another screenshot.

        Returns:
            tuple: Color (r, g, b).
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: color, area, image, load
- Signals: TF-IDF -0.033, encoder -0.034
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 3. tornadoweb/tornado :: HTTPServer.start  (`f7d0a6abdd9f`)

Code diff:
```diff
- def start(self, num_processes=None):
+ def start(self, num_processes=1):
-         if num_processes is None:
+         if num_processes is None or num_processes <= 0:
```

### Docstring before commit -> **potential_drift**
```text
Starts this server in the IOLoop.

        By default, we detect the number of cores available on this machine
        and fork that number of child processes. If num_processes is given, we
        fork that specific number of sub-processes.

        If num_processes is 1 or we detect only 1 CPU core, we run the server
        in this process and do not fork any additional child process.

        Since we use processes and not threads, there is no shared memory
        between any server code.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: processes, fork, num, loop, io
- Signals: TF-IDF +0.005, encoder -0.025
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **potential_drift**
```text
Starts this server in the IOLoop.

        By default, we run the server in this process and do not fork any
        additional child process.

        If num_processes is None or <= 0, we detect the number of cores
        available on this machine and fork that number of child
        processes. If num_processes is given and > 1, we fork that
        specific number of sub-processes.

        Since we use processes and not threads, there is no shared memory
        between any server code.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: processes, fork, num, loop, io
- Signals: TF-IDF +0.004, encoder -0.028
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 4. tornadoweb/tornado :: parse_qs_bytes  (`fcf40a99b17f`)

Code diff:
```diff
-     qs: str, keep_blank_values: bool = False, strict_parsing: bool = False
+     qs: Union[str, bytes], keep_blank_values: bool = False, strict_parsing: bool = False
+     if isinstance(qs, bytes):
+         qs = qs.decode("latin1")
```

### Docstring before commit -> **potential_drift**
```text
Parses a query string like urlparse.parse_qs, but returns the
    values as byte strings.

    Keys still become type str (interpreted as latin1 in python3!)
    because it's too painful to keep them as byte strings in
    python3 and in practice they're nearly always ascii anyway.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: qs, python3, keep, parse, values
- Signals: TF-IDF +0.001, encoder -0.050
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **potential_drift**
```text
Parses a query string like urlparse.parse_qs,
    but takes bytes and returns the values as byte strings.

    Keys still become type str (interpreted as latin1 in python3!)
    because it's too painful to keep them as byte strings in
    python3 and in practice they're nearly always ascii anyway.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: qs, python3, bytes, keep, parse
- Signals: TF-IDF +0.008, encoder -0.049
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 5. locustio/locust :: StatsEntry.extend  (`35950e497c3a`)

Code diff:
```diff
- def extend(self, other, full_request_history=False):
+ def extend(self, other):
-         
+          
-         if full_request_history:
-             for key in other.response_times:
+         for key in other.response_times:
-                 self.response_times[key] = self.response_times.get(key, 0) + other.response_times[key]
+             self.response_times[key] = self.response_times.get(key, 0) + other.response_times[key]
-             for key in other.num_reqs_per_sec:
+         for key in other.num_reqs_per_sec:
-                 self.num_reqs_per_sec[key] = self.num_reqs_per_sec.get(key, 0) +  other.num_reqs_per_sec[key]
+             self.num_reqs_per_sec[key] = self.num_reqs_per_sec.get(key, 0) +  other.num_reqs_per_sec[key]
-         else:
-             # still add the number of reqs per seconds the last 20 seconds
-             for i in xrange(other.last_request_timestamp-20, other.last_request_timestamp+1):
-                 if i in other.num_reqs_per_sec:
-                     self.num_reqs_per_sec[i] = self.num_reqs_per_sec.get(i, 0) + other.num_reqs_per_sec[i]
```

### Docstring before commit -> **potential_drift**
```text
Extend the data fro the current StatsEntry with the stats from another
        StatsEntry instance. 
        
        If full_request_history is False, we'll only care to add the data from 
        the last 20 seconds of other's stats. The reason for this argument is that 
        extend can be used to generate an aggregate of multiple different StatsEntry 
        instances on the fly, in order to get the *total* current RPS, average 
        response time, etc.
```
- Summary: The documentation mentions `add`, `full`, `history`, `seconds`, which this change removed from the code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: add, full, history, seconds | lines: - def extend(self, other, full_request_history=False): / - if full_request_history: / - # still add the number of reqs per seconds the last 20 seconds
- Evidence [term_overlap]: Terms shared with the current code: other, total, response, time, last
- Signals: TF-IDF -0.059, encoder -0.091
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Check whether statements about `add`, `full`, `history` still hold after the change.

### Docstring after commit -> **no_obvious_drift**
```text
Extend the data from the current StatsEntry with the stats from another
        StatsEntry instance.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: extend
- Signals: TF-IDF -0.005, encoder +0.025
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 6. pytorch/pytorch :: ModuleList.extend  (`6ff2d3fcfce4`)

Code diff:
```diff
-         if not isinstance(modules, list):
+         if not isinstance(modules, Iterable):
-             raise TypeError("ModuleList.extend should be called with a "
+             raise TypeError("ModuleList.extend should be called with an "
-                             "list, but got " + type(modules).__name__)
+                             "iterable, but got " + type(modules).__name__)
```

### Docstring before commit -> **potential_drift**
```text
r"""Appends modules from a Python list at the end.

        Arguments:
            modules (list): list of modules to append
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: modules, list
- Signals: TF-IDF -0.048, encoder -0.047
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **no_obvious_drift**
```text
r"""Appends modules from a Python iterable to the end of the list.

        Arguments:
            modules (iterable): iterable of modules to append
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: modules, iterable, list
- Signals: TF-IDF +0.136, encoder +0.037
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 7. zulip/zulip :: GetSubscribersTest.check_well_formed_result  (`cea215b339d0`)

Code diff:
```diff
-             user_profile.email
-             for user_profile in self.users_subscribed_to_stream(stream_name, realm)
+             user_profile.id for user_profile in self.users_subscribed_to_stream(stream_name, realm)
```

### Docstring before commit -> **potential_drift**
```text
A successful call to get_subscribers returns the list of subscribers in
        the form:

        {"msg": "",
         "result": "success",
         "subscribers": [self.example_email("hamlet"), self.example_email("prospero")]}
```
- Summary: The documentation mentions `email`, which this change removed from the code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: email | lines: - user_profile.email
- Evidence [term_overlap]: Terms shared with the current code: result, self, list, in, to
- Signals: TF-IDF -0.117, encoder -0.051
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Check whether statements about `email` still hold after the change.

### Docstring after commit -> **no_obvious_drift**
```text
A successful call to get_subscribers returns the list of subscribers in
        the form:

        {"msg": "",
         "result": "success",
         "subscribers": [hamlet_user.id, prospero_user.id]}
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: user, result, id, list, in
- Signals: TF-IDF +0.039, encoder -0.004
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 8. Textualize/textual :: ProgressBar.update  (`f257fe21ffa4`)

Code diff:
```diff
-         total: float | None = None,
-         progress: float | None = None,
-         advance: float | None = None,
+         total: None | float | UnusedParameter = UNUSED,
+         progress: float | UnusedParameter = UNUSED,
+         advance: float | UnusedParameter = UNUSED,
-         if total is not None:
+         if not isinstance(total, UnusedParameter):
-         if progress is not None:
+         if not isinstance(progress, UnusedParameter):
-         if advance is not None:
+         if not isinstance(advance, UnusedParameter):
```

### Docstring before commit -> **potential_drift**
```text
Update the progress bar with the given options.

        Options only affect the progress bar if they are not `None`.

        Example:
            ```py
            progress_bar.update(
                total=200,  # Set new total to 200 steps.
                progress=None,  # This has no effect.
            )
            ```

        Args:
            total: New total number of steps (if not `None`).
            progress: Set the progress to the given number of steps (if not `None`).
            advance: Advance the progress by this number of steps (if not `None`).
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: progress, advance, total, update, not
- Signals: TF-IDF -0.169, encoder -0.070
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **potential_drift**
```text
Update the progress bar with the given options.

        Example:
            ```py
            progress_bar.update(
                total=200,  # Set new total to 200 steps.
                progress=50,  # Set the progress to 50 (out of 200).
            )
            ```

        Args:
            total: New total number of steps.
            progress: Set the progress to the given number of steps.
            advance: Advance the progress by this number of steps.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: progress, advance, total, update
- Signals: TF-IDF -0.156, encoder -0.032
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 9. mvt-project/mvt :: DownloadAPKs.__init__  (`d8d5e14a548b`)

Code diff:
```diff
- def __init__(self, output_folder=None, all_apks=False, log=None,
+ def __init__(self, results_path: str = "", all_apks: bool = False,
-                  packages=None):
+                  packages: list = []):
-         super().__init__(log=log)
+         super().__init__(results_path=results_path, log=log)
-         self.output_folder_apk = None
+         self.results_path_apks = None
-         self.output_folder = output_folder
```

### Docstring before commit -> **potential_drift**
```text
Initialize module.
        :param output_folder: Path to the folder where data should be stored
        :param all_apks: Boolean indicating whether to download all packages
                         or filter known-goods
        :param packages: Provided list of packages, typically for JSON checks
```
- Summary: The documentation describes parameter(s) `output_folder` that the current code does not have.
- Evidence [rule_r1]: Documented but not in the signature: output_folder | lines: def __init__(self, results_path: str = "", all_apks: bool = False,
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: folder, output | lines: - def __init__(self, output_folder=None, all_apks=False, log=None, / - self.output_folder_apk = None / - self.output_folder = output_folder
- Evidence [term_overlap]: Terms shared with the current code: packages, all, path, list
- Signals: TF-IDF -0.093, encoder +0.020
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Update the parameter list: remove or rename `output_folder` to match the signature.

### Docstring after commit -> **no_obvious_drift**
```text
Initialize module.
        :param results_path: Path to the folder where data should be stored
        :param all_apks: Boolean indicating whether to download all packages
                         or filter known-goods
        :param packages: Provided list of packages, typically for JSON checks
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: folder | lines: - def __init__(self, output_folder=None, all_apks=False, log=None, / - self.output_folder_apk = None / - self.output_folder = output_folder
- Evidence [term_overlap]: Terms shared with the current code: packages, results, path, all, list
- Signals: TF-IDF +0.093, encoder +0.126
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 10. espnet/espnet :: CustomConverter.__call__  (`77c4f8608eb2`)

Code diff:
```diff
- def __call__(self, batch, device=torch.device('cpu')):
+ def __call__(self, batch, device):
-         ys = list(ys)  # Convert zip object to list in python 3.x
+         # Convert zip object to list in python 3.x
+         ys = list(ys)
+         # currently only support real number
+         if xs[0].dtype.kind == 'c':
+             xs_pad_real = pad_list(
+                 [torch.from_numpy(x.real).float() for x in xs], 0).to(device, dtype=self.dtype)
+             xs_pad_imag = pad_list(
+                 [torch.from_numpy(x.imag).float() for x in xs], 0).to(device, dtype=self.dtype)
+             # Note(kamo):
+             # {'real': ..., 'imag': ...} will be changed to ComplexTensor in E2E.
+             # Don't create ComplexTensor and give it to E2E here
+             # because torch.nn.DataParallel can't handle it.
+             xs_pad = {'real': xs_pad_real, 'imag': xs_pad_imag}
+         else:
-         xs_pad = pad_list([torch.from_numpy(x).float() for x in xs], 0).to(device)
+             xs_pad = pad_list([torch.from_numpy(x).float() for x in xs], 0).to(device, dtype=self.dtype)
+ 
+         # TODO(Xuankai): try to make this neat
+         if not isinstance(ys[0], np.ndarray):
-         ys_pad = [torch.from_numpy(y[0]).long() for y in ys] + [torch.from_numpy(y[1]).long() for y in ys]
+             ys_pad = [torch.from_numpy(y[0]).long() for y in ys] + [torch.from_numpy(y[1]).long() for y in ys]
-         ys_pad = pad_list(ys_pad, self.ignore_id)
```

### Docstring before commit -> **potential_drift**
```text
Transforms a batch and send it to a device.

        Args:
            batch (list(tuple(str, dict[str, dict[str, Any]]))): The batch to transform.
            device (torch.device): The device to send to.

        Returns:
            tuple(torch.Tensor, torch.Tensor, torch.Tensor): Transformed batch.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: torch, device, batch, tensor, to
- Signals: TF-IDF -0.014, encoder -0.124
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

### Docstring after commit -> **potential_drift**
```text
Transform a batch and send it to a device.

        Args:
            batch (list(tuple(str, dict[str, dict[str, Any]]))): The batch to transform.
            device (torch.device): The device to send to.

        Returns:
            tuple(torch.Tensor, torch.Tensor, torch.Tensor): Transformed batch.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: torch, device, batch, tensor, to
- Signals: TF-IDF -0.014, encoder -0.123
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 11. huggingface/transformers :: window_reverse  (`031ecf76a550`)

Code diff:
```diff
+     num_channels = windows.shape[-1]
-     batch_size = int(windows.shape[0] / (height * width / window_size / window_size))
- 
-     hidden_states = windows.view(batch_size, height // window_size, width // window_size, window_size, window_size, -1)
+     windows = windows.view(-1, height // window_size, width // window_size, window_size, window_size, num_channels)
-     hidden_states = hidden_states.permute(0, 1, 3, 2, 4, 5).contiguous().view(batch_size, height, width, -1)
-     return hidden_states
+     windows = windows.permute(0, 1, 3, 2, 4, 5).contiguous().view(-1, height, width, num_channels)
+     return windows
```

### Docstring before commit -> **no_obvious_drift**
```text
Args:
        windows (`torch.FloatTensor` of shape `(num_windows * batch_size, window_size, window_size, num_channels)`):
            Input windows
        window_size (`int`):
            Window size
        height (`int`):
            Height of the resized audio
        width (`int`):
            Width of the resized audio
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: batch | lines: - batch_size = int(windows.shape[0] / (height * width / window_size / window_size)) / - hidden_states = windows.view(batch_size, height // window_size, width // window_size, window_size, window_size, -1) / - hidden_states = hidden_states.permute(0, 1, 3, 2, 4, 5).contiguous().view(batch_size, height, width, -1)
- Evidence [term_overlap]: Terms shared with the current code: window, windows, height, size, width
- Signals: TF-IDF +0.127, encoder +0.021
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Merges windows to produce higher resolution features.
    Args:
        windows (`torch.FloatTensor` of shape `(num_windows * batch_size, window_size, window_size, num_channels)`):
            Input windows
        window_size (`int`):
            Window size
        height (`int`):
            Height of the resized audio
        width (`int`):
            Width of the resized audio
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: batch | lines: - batch_size = int(windows.shape[0] / (height * width / window_size / window_size)) / - hidden_states = windows.view(batch_size, height // window_size, width // window_size, window_size, window_size, -1) / - hidden_states = hidden_states.permute(0, 1, 3, 2, 4, 5).contiguous().view(batch_size, height, width, -1)
- Evidence [term_overlap]: Terms shared with the current code: windows, window, height, size, width
- Signals: TF-IDF +0.123, encoder +0.047
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 12. matplotlib/matplotlib :: Axes.axline  (`daf5fa9f64fd`)

Code diff:
```diff
-         if not self.get_xscale() == self.get_yscale() == 'linear':
-             raise NotImplementedError('axline() is only supported on '
-                                       'linearly scaled axes')
-                             "axline generates its own transform.")
+                             "axline generates its own transform")
- 
-         # If x values the same, we have a vertical line
-         if np.allclose(x1, x2):
-             if np.allclose(y1, y2):
-                 raise ValueError(
-                     'Cannot draw a line through two identical points '
-                     f'(got x1={x1}, x2={x2}, y1={y1}, y2={y2}).')
-             line = self.axvline(x1, **kwargs)
-             return line
+         line = mlines._AxLine([x1, x2], [y1, y2], **kwargs)
+         # Like add_line, but correctly handling data limits.
+         self._set_artist_props(line)
+         if line.get_clip_path() is None:
+             line.set_clip_path(self.patch)
+         if not line.get_label():
+             line.set_label(f"_line{len(self.lines)}")
+         self.lines.append(line)
+         line._remove_method = self.lines.remove
+         self.update_datalim([xy1, xy2])
+         self._request_autoscale_view()
```

### Docstring before commit -> **no_obvious_drift**
```text
Add an infinitely long straight line that passes through two points.

        Parameters
        ----------
        xy1, xy2 : (float, float)
            Points for the line to pass through.

        Returns
        -------
        :class:`~matplotlib.lines.Line2D`

        Other Parameters
        ----------------
        Valid kwargs are :class:`~matplotlib.lines.Line2D` properties,
        with the exception of 'transform':

        %(_Line2D_docstr)s

        Examples
        --------
        Draw a thick red line passing through (0, 0) and (1, 1)::

            >>> axline((0, 0), (1, 1), linewidth=4, color='r')


        See Also
        --------
        axhline : for horizontal lines
        axvline : for vertical lines

        Notes
        -----
        Currently this method does not work properly with non-linear axes.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: axes, axvline, draw, line2, linear | lines: - if not self.get_xscale() == self.get_yscale() == 'linear': / - 'linearly scaled axes') / - # If x values the same, we have a vertical line
- Evidence [term_overlap]: Terms shared with the current code: line, lines, transform, kwargs, add
- Signals: TF-IDF +0.004, encoder +0.078
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: The function accepts **kwargs, so documented-but-unlisted parameters (Valid, with) may be valid; not treated as evidence.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Add an infinitely long straight line that passes through two points.

        This draws a straight line "on the screen", regardless of the x and y
        scales, and is thus also suitable for drawing exponential decays in
        semilog plots, power laws in loglog plots, etc.

        Parameters
        ----------
        xy1, xy2 : (float, float)
            Points for the line to pass through.

        Returns
        -------
        :class:`~matplotlib.lines.Line2D`

        Other Parameters
        ----------------
        **kwargs
            Valid kwargs are :class:`~matplotlib.lines.Line2D` properties,
            with the exception of 'transform':

            %(_Line2D_docstr)s

        Examples
        --------
        Draw a thick red line passing through (0, 0) and (1, 1)::

            >>> axline((0, 0), (1, 1), linewidth=4, color='r')

        See Also
        --------
        axhline : for horizontal lines
        axvline : for vertical lines
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: axvline, draw, line2, points, through | lines: - # If x values the same, we have a vertical line / - 'Cannot draw a line through two identical points ' / - line = self.axvline(x1, **kwargs)
- Evidence [term_overlap]: Terms shared with the current code: line, lines, transform, kwargs, add
- Signals: TF-IDF +0.022, encoder +0.014
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 13. pandas-dev/pandas :: ExtensionDtype.construct_from_string  (`1e0c7304534a`)

Code diff:
```diff
-             raise TypeError("Expects a string, got {typ}".format(typ=type(string)))
+             raise TypeError(f"Expects a string, got {type(string).__name__}")
+             raise TypeError(f"Cannot construct a '{cls.__name__}' from '{string}'")
-             raise TypeError(
-                 "Cannot construct a '{cls}' from '{string}'".format(
-                     cls=cls.__name__, string=string
-                 )
-             )
```

### Docstring before commit -> **no_obvious_drift**
```text
r"""
        Construct this type from a string.

        This is useful mainly for data types that accept parameters.
        For example, a period dtype accepts a frequency parameter that
        can be set as ``period[H]`` (where H means hourly frequency).

        By default, in the abstract class, just the name of the type is
        expected. But subclasses can overwrite this method to accept
        parameters.

        Parameters
        ----------
        string : str
            The name of the type, for example ``category``.

        Returns
        -------
        ExtensionDtype
            Instance of the dtype.

        Raises
        ------
        TypeError
            If a class cannot be constructed from this 'string'.

        Examples
        --------
        For extension dtypes with arguments the following may be an
        adequate implementation.

        >>> @classmethod
        ... def construct_from_string(cls, string):
        ...     pattern = re.compile(r"^my_type\[(?P<arg_name>.+)\]$")
        ...     match = pattern.match(string)
        ...     if match:
        ...         return cls(**match.groupdict())
        ...     else:
        ...         raise TypeError("Cannot construct a '{}' from "
        ...                         "'{}'".format(cls.__name__, string))
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: format | lines: - raise TypeError("Expects a string, got {typ}".format(typ=type(string))) / - "Cannot construct a '{cls}' from '{string}'".format(
- Evidence [term_overlap]: Terms shared with the current code: construct, cls, string, type, cannot
- Signals: TF-IDF +0.033, encoder +0.009
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
r"""
        Construct this type from a string.

        This is useful mainly for data types that accept parameters.
        For example, a period dtype accepts a frequency parameter that
        can be set as ``period[H]`` (where H means hourly frequency).

        By default, in the abstract class, just the name of the type is
        expected. But subclasses can overwrite this method to accept
        parameters.

        Parameters
        ----------
        string : str
            The name of the type, for example ``category``.

        Returns
        -------
        ExtensionDtype
            Instance of the dtype.

        Raises
        ------
        TypeError
            If a class cannot be constructed from this 'string'.

        Examples
        --------
        For extension dtypes with arguments the following may be an
        adequate implementation.

        >>> @classmethod
        ... def construct_from_string(cls, string):
        ...     pattern = re.compile(r"^my_type\[(?P<arg_name>.+)\]$")
        ...     match = pattern.match(string)
        ...     if match:
        ...         return cls(**match.groupdict())
        ...     else:
        ...         raise TypeError(f"Cannot construct a '{cls.__name__}' from
        ...             " "'{string}'")
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: construct, cls, string, type, cannot
- Signals: TF-IDF +0.047, encoder +0.009
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 14. SAML-Toolkits/python3-saml :: OneLogin_Saml2_Metadata.add_x509_key_descriptors  (`27160876c7dc`)

Code diff:
```diff
- def add_x509_key_descriptors(metadata, cert=None):
+ def add_x509_key_descriptors(metadata, cert=None, add_encryption=True):
+         if add_encryption:
-         OneLogin_Saml2_Metadata.__add_x509_key_descriptors(sp_sso_descriptor, cert, False)
+             OneLogin_Saml2_Metadata.__add_x509_key_descriptors(sp_sso_descriptor, cert, False)
```

### Docstring before commit -> **no_obvious_drift**
```text
Adds the x509 descriptors (sign/encryption) to the metadata
        The same cert will be used for sign/encrypt

        :param metadata: SAML Metadata XML
        :type metadata: string

        :param cert: x509 cert
        :type cert: string

        :returns: Metadata with KeyDescriptors
        :rtype: string
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: cert, x509, descriptors, metadata, encryption
- Signals: TF-IDF +0.032, encoder +0.010
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Adds the x509 descriptors (sign/encryption) to the metadata
        The same cert will be used for sign/encrypt

        :param metadata: SAML Metadata XML
        :type metadata: string

        :param cert: x509 cert
        :type cert: string

        :param add_encryption: Determines if the KeyDescriptor[use="encryption"] should be added.
        :type add_encryption: boolean

        :returns: Metadata with KeyDescriptors
        :rtype: string
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: cert, x509, encryption, descriptors, metadata
- Signals: TF-IDF +0.083, encoder +0.028
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 15. byt3bl33d3r/CrackMapExec :: CMEModule.options  (`67999c454f6b`)

Code diff:
```diff
+         self.base_dn = None
+         if module_options and "BASE_DN" in module_options:
+             self.base_dn = module_options["BASE_DN"]
```

### Docstring before commit -> **no_obvious_drift**
```text
SERVER             PKI Enrollment Server to enumerate templates for. Default is None, use CN name
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: server, none
- Signals: TF-IDF -0.035, encoder +0.064
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
SERVER             PKI Enrollment Server to enumerate templates for. Default is None, use CN name
        BASE_DN            The base domain name for the LDAP query
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: server, base, none
- Signals: TF-IDF +0.085, encoder +0.133
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 16. pandas-dev/pandas :: OpenpyxlReader.__init__  (`247af111e091`)

Code diff:
```diff
+         engine_kwargs: dict | None = None,
-         super().__init__(filepath_or_buffer, storage_options=storage_options)
+         super().__init__(
+             filepath_or_buffer,
+             storage_options=storage_options,
+             engine_kwargs=engine_kwargs,
+         )
```

### Docstring before commit -> **no_obvious_drift**
```text
Reader using openpyxl engine.

        Parameters
        ----------
        filepath_or_buffer : str, path object or Workbook
            Object to be parsed.
        {storage_options}
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: filepath, storage, engine, buffer, options
- Signals: TF-IDF +0.051, encoder -0.017
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Reader using openpyxl engine.

        Parameters
        ----------
        filepath_or_buffer : str, path object or Workbook
            Object to be parsed.
        {storage_options}
        engine_kwargs : dict, optional
            Arbitrary keyword arguments passed to excel engine.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: engine, filepath, storage, buffer, options
- Signals: TF-IDF +0.187, encoder +0.053
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 17. PostHog/posthog :: retrieve_entity_from  (`9aa2422d8e9c`)

Code diff:
```diff
- def retrieve_entity_from(entity_id: Union[str, int], events: List[Dict], actions: List[Dict]) -> Optional[Dict]:
+ def retrieve_entity_from(entity_id: str, events: List[Dict], actions: List[Dict]) -> Optional[Dict]:
-         if action.get("id") == entity_id:
+         if str(action.get("id")) == entity_id:
```

### Docstring before commit -> **no_obvious_drift**
```text
Retrieves the entity from the events and actions.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: entity, events, actions, from
- Signals: TF-IDF +0.005, encoder +0.053
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **inconclusive**
```text
Retrieves the entity from the events and actions.

    NOTE: entity_id here is considered always to be a string. event ids are
    strings, and action ids are ints. Elsewhere we get the `entity_id` from a
    get request, from which we do not get type information, and we do not
    require the entity type to be provided. A more complete solution might be to
    require entity type information, but to resolve the issue we cast the action
    id to a string, such that we can get equality.

    This doesn't preclude ths issue that an event name could be a string that is
    also a valid number however, but this should be an unlikely occurance.
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: entity, action, event, events, actions
- Signals: TF-IDF +0.004, encoder -0.014
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

## 18. google-research/text-to-text-transfer-transformer :: Feature.__init__  (`050a32902702`)

Code diff:
```diff
- def __init__(self, vocabulary, add_eos=True, required=True):
+ def __init__(
+       self,
+       vocabulary: Union[Callable[[], Vocabulary], Vocabulary],
+       add_eos: bool = True,
+       required: bool = True):
```

### Docstring before commit -> **no_obvious_drift**
```text
Create a Feature instance.

    Args:
      vocabulary: vocabularies.Vocabulary object to use for tokenization,
        or a callable function returning a vocabulary
      add_eos: bool, whether an EOS token should be added to this Feature.
      required: Whether or not this feature must exist in the final outputs
        of the Task.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: vocabulary, eos, required, add, callable
- Signals: TF-IDF +0.032, encoder +0.062
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Create a Feature instance.

    Args:
      vocabulary: vocabularies.Vocabulary object to use for tokenization, or a
        callable function returning a vocabulary
      add_eos: bool, whether an EOS token should be added to this Feature.
      required: Whether or not this feature must exist in the final outputs of
        the Task.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: vocabulary, eos, required, add, callable
- Signals: TF-IDF +0.032, encoder +0.062
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 19. matplotlib/matplotlib :: ColorbarBase._mesh  (`f479be4d1896`)

Code diff:
```diff
-         # if boundaries and values are None, then we can go ahead and
-         # scale this up for Auto tick location.  Otherwise we
-         # want to keep normalized between 0 and 1 and use manual tick
-         # locations.
- 
+         # copy the norm and change the vmin and vmax to the vmin and
+         # vmax of the colorbar, not the norm.  This allows the situation
+         # where the colormap has a narrower range than the colorbar, to
+         # accomodate extra contours:
+         norm = copy.copy(self.norm)
+         norm.vmin = self.vmin
+         norm.vmax = self.vmax
-         if self._use_auto_colorbar_locator():
+         xmid = np.array([0.5])
+         try:
-             y = self.norm.inverse(y)
+             y = norm.inverse(y)
-             x = self.norm.inverse(x)
+             x = norm.inverse(x)
+             xmid = norm.inverse(xmid)
+         except ValueError:
+             # occurs for norms that don't have an inverse, in
+             # which case manually scale:
+             dv = self.vmax - self.vmin
+             x = x * dv + self.vmin
```

### Docstring before commit -> **no_obvious_drift**
```text
Return X,Y, the coordinate arrays for the colorbar pcolormesh.
        These are suitable for a vertical colorbar; swapping and
        transposition for a horizontal colorbar are done outside
        this function.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: the, and, for, this, return
- Signals: TF-IDF -0.004, encoder +0.075
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Return X,Y, the coordinate arrays for the colorbar pcolormesh.
        These are suitable for a vertical colorbar; swapping and
        transposition for a horizontal colorbar are done outside
        this function.

        These are scaled between vmin and vmax
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [rule_r2]: Mentioned in the docs but removed from the code: between | lines: - # want to keep normalized between 0 and 1 and use manual tick
- Evidence [term_overlap]: Terms shared with the current code: and, the, for, this, return
- Signals: TF-IDF -0.028, encoder +0.122
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Uncertainty: Removed identifiers are mentioned, but the similarity signals say the documentation fits the new code; not treated as decisive.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 20. pandas-dev/pandas :: Series.to_dict  (`a8b4f7d96e25`)

Code diff:
```diff
- def to_dict(self):
+ def to_dict(self, into=dict):
+         # GH16122
+         into_c = standardize_mapping(into)
-         return dict(compat.iteritems(self))
+         return into_c(compat.iteritems(self))
```

### Docstring before commit -> **no_obvious_drift**
```text
Convert Series to {label -> value} dict

        Returns
        -------
        value_dict : dict
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: dict, to
- Signals: TF-IDF -0.068, encoder +0.085
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

### Docstring after commit -> **no_obvious_drift**
```text
Convert Series to {label -> value} dict or dict-like object.

        Parameters
        ----------
        into : class, default dict
            The collections.Mapping subclass to use as the return
            object. Can be the actual class or an empty
            instance of the mapping type you want.  If you want a
            collections.defaultdict, you must pass it initialized.

            .. versionadded:: 0.21.0

        Returns
        -------
        value_dict : collections.Mapping

        Examples
        --------
        >>> s = pd.Series([1, 2, 3, 4])
        >>> s.to_dict()
        {0: 1, 1: 2, 2: 3, 3: 4}
        >>> from collections import OrderedDict, defaultdict
        >>> s.to_dict(OrderedDict)
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> dd = defaultdict(list)
        >>> s.to_dict(dd)
        defaultdict(<type 'list'>, {0: 1, 1: 2, 2: 3, 3: 4})
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: mapping, dict, into, to, return
- Signals: TF-IDF +0.076, encoder +0.153
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 21. espnet/espnet :: ESPnetEnhancementModel._compute_loss  (`cfa79d289e47`)

Code diff:
```diff
+                 ]
+                 pass
+ 
+             if spectrum_pre is not None and not isinstance(
+                 spectrum_pre[0], ComplexTensor
+             ):
+                 spectrum_pre = [
+                     ComplexTensor(*torch.unbind(sp, dim=-1)) for sp in spectrum_pre
```

### Docstring before commit -> **inconclusive**
```text
Compute loss according to self.loss_type.

        Args:
            speech_mix: (Batch, samples) or (Batch, samples, channels)
            speech_lengths: (Batch,), default None for chunk interator,
                            because the chunk-iterator does not have the
                            speech_lengths returned. see in
                            espnet2/iterators/chunk_iter_factory.py
            speech_ref: (Batch, num_speaker, samples)
                        or (Batch, num_speaker, samples, channels)
            dereverb_speech_ref: (Batch, N, samples)
                        or (Batch, num_speaker, samples, channels)
            noise_ref: (Batch, num_noise_type, samples)
                        or (Batch, num_speaker, samples, channels)
            cal_loss: whether to calculate enh loss, defualt is True

        Returns:
            loss: (torch.Tensor) speech enhancement loss
            speech_pre: (List[torch.Tensor] or List[ComplexTensor])
                        enhanced speech or spectrum(s)
            others: (OrderedDict) estimated masks or None
            output_lengths: (Batch,)
            perm: () best permutation
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: speech, loss, lengths, noise, ref
- Signals: TF-IDF +0.003, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **inconclusive**
```text
Compute loss according to self.loss_type.

        Args:
            speech_mix: (Batch, samples) or (Batch, samples, channels)
            speech_lengths: (Batch,), default None for chunk interator,
                            because the chunk-iterator does not have the
                            speech_lengths returned. see in
                            espnet2/iterators/chunk_iter_factory.py
            speech_ref: (Batch, num_speaker, samples)
                        or (Batch, num_speaker, samples, channels)
            dereverb_speech_ref: (Batch, N, samples)
                        or (Batch, num_speaker, samples, channels)
            noise_ref: (Batch, num_noise_type, samples)
                        or (Batch, num_speaker, samples, channels)
            cal_loss: whether to calculate enh loss, default is True

        Returns:
            loss: (torch.Tensor) speech enhancement loss
            speech_pre: (List[torch.Tensor] or List[ComplexTensor])
                        enhanced speech or spectrum(s)
            others: (OrderedDict) estimated masks or None
            output_lengths: (Batch,)
            perm: () best permutation
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: speech, loss, lengths, noise, ref
- Signals: TF-IDF +0.003, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

## 22. matplotlib/matplotlib :: YAxis._update_label_postion  (`64e68c17577e`)

Code diff:
```diff
- def _update_label_postion(self, bboxes):
+ def _update_label_postion(self, bboxes, bboxes2):
-         
+          
+         if self.label_position == 'left':
-         if not len(bboxes):
+             if not len(bboxes):
-             left = self.axes.bbox.xmin()
+                 left = self.axes.bbox.xmin()
+             else:
+ 
+                 bbox = bbox_all(bboxes)
+                 left = bbox.xmin()
+             
+             self.label.set_position( (left-self.LABELPAD*self.figure.dpi.get()/72.0, y))
+ 
+             if not len(bboxes2):
+                 right = self.axes.bbox.xmax()
+             else:
+ 
-             bbox = bbox_all(bboxes)
+                 bbox = bbox_all(bboxes2)
-             left = bbox.xmin()
+                 right = bbox.xmax()
+             
```

### Docstring before commit -> **inconclusive**
```text
Update the label position based on the sequence of bounding
        boxes overlaps of all the ticklabels that overlap the current
        ticklabel.  overlaps are the bounding boxes of the ticklabels
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: label, position, all, update
- Signals: TF-IDF -0.003, encoder -0.011
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **inconclusive**
```text
Update the label position based on the sequence of bounding
        boxes of all the ticklabels
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: label, position, all, update
- Signals: TF-IDF -0.005, encoder -0.012
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

## 23. stratosphereips/StratosphereLinuxIPS :: Main.close_all_ports  (`4252ec47349d`)

Code diff:
```diff
-         for port in range(self.start_port, self.end_port + 1):
+         slips_supported_range = [port for port in range(self.start_port, self.end_port + 1)]
+         slips_supported_range.append(6379)
+         for port in slips_supported_range:
+ 
```

### Docstring before commit -> **inconclusive**
```text
Closes all the redis ports
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: redis, ports, closes, all, the
- Signals: TF-IDF -0.012, encoder -0.011
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
Closes all the redis ports  in logfile and in slips supported range of ports
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: redis, ports, logfile, closes, supported
- Signals: TF-IDF +0.020, encoder +0.025
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 24. pandas-dev/pandas :: DatetimeIndex.to_series  (`7ebf17aa6bf3`)

Code diff:
```diff
- def to_series(self, keep_tz=False):
+ def to_series(self, keep_tz=False, index=None, name=None):
-         return Series(self._to_embed(keep_tz),
+ 
+         if index is None:
-                       index=self._shallow_copy(),
+             index = self._shallow_copy()
+         if name is None:
-                       name=self.name)
+             name = self.name
+ 
+         return Series(self._to_embed(keep_tz), index=index, name=name)
```

### Docstring before commit -> **inconclusive**
```text
Create a Series with both index and values equal to the index keys
        useful with map for returning an indexer based on an index

        Parameters
        ----------
        keep_tz : optional, defaults False.
            return the data keeping the timezone.

            If keep_tz is True:

              If the timezone is not set, the resulting
              Series will have a datetime64[ns] dtype.

              Otherwise the Series will have an datetime64[ns, tz] dtype; the
              tz will be preserved.

            If keep_tz is False:

              Series will have a datetime64[ns] dtype. TZ aware
              objects will have the tz removed.

        Returns
        -------
        Series
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: tz, series, keep, index, false
- Signals: TF-IDF -0.002, encoder +0.002
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
Create a Series with both index and values equal to the index keys
        useful with map for returning an indexer based on an index

        Parameters
        ----------
        keep_tz : optional, defaults False.
            return the data keeping the timezone.

            If keep_tz is True:

              If the timezone is not set, the resulting
              Series will have a datetime64[ns] dtype.

              Otherwise the Series will have an datetime64[ns, tz] dtype; the
              tz will be preserved.

            If keep_tz is False:

              Series will have a datetime64[ns] dtype. TZ aware
              objects will have the tz removed.
        index : Index, optional
            index of resulting Series. If None, defaults to original index
        name : string, optional
            name of resulting Series. If None, defaults to name of original
            index

        Returns
        -------
        Series
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: series, tz, index, keep, name
- Signals: TF-IDF +0.032, encoder +0.002
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 25. stratosphereips/StratosphereLinuxIPS :: Main.update_host_ip  (`50bb77bfd493`)

Code diff:
```diff
- def update_host_ip(self, hostIP, modified_profiles) -> str:
+ def update_host_ip(self, hostIP: str, modified_profiles: Set[str]) -> str:
```

### Docstring before commit -> **inconclusive**
```text
when running on an interface we keep track of the host IP. If there was no
        # modified TWs in the host IP, we check if the network was changed.
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: ip, host, modified, interface, if
- Signals: TF-IDF -0.012, encoder +0.006
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **inconclusive**
```text
when running on an interface we keep track of the host IP.
        If there was no  modified TWs in the host IP, we check if the
        network was changed.
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: ip, host, modified, interface, if
- Signals: TF-IDF -0.012, encoder +0.009
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Next step: Review manually: compare the documentation with the code diff.

## 26. tornadoweb/tornado :: RequestHandler.set_cookie  (`6d79fa104be7`)

Code diff:
```diff
+         **kwargs: Any,
- 
+         if kwargs:
+             # The setitem interface is case-insensitive, so continue to support
+             # kwargs for backwards compatibility until we can remove deprecated
+             # features.
+             for k, v in kwargs.items():
+                 morsel[k] = v
+             warnings.warn(
+                 f"Deprecated arguments to set_cookie: {set(kwargs.keys())} "
+                 "(should be lowercase)",
+                 DeprecationWarning,
+             )
```

### Docstring before commit -> **inconclusive**
```text
Sets an outgoing cookie name/value with the given options.

        Newly-set cookies are not immediately visible via `get_cookie`;
        they are not present until the next request.

        Most arguments are passed directly to `http.cookies.Morsel` directly.
        See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie
        for more information.

        ``expires`` may be a numeric timestamp as returned by `time.time`,
        a time tuple as returned by `time.gmtime`, or a
        `datetime.datetime` object. ``expires_days`` is provided as a convenience
        to set an expiration time in days from today (if both are set, ``expires``
        is used).
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: cookie, expires, cookies, days, datetime
- Signals: TF-IDF -0.005, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
Sets an outgoing cookie name/value with the given options.

        Newly-set cookies are not immediately visible via `get_cookie`;
        they are not present until the next request.

        Most arguments are passed directly to `http.cookies.Morsel` directly.
        See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie
        for more information.

        ``expires`` may be a numeric timestamp as returned by `time.time`,
        a time tuple as returned by `time.gmtime`, or a
        `datetime.datetime` object. ``expires_days`` is provided as a convenience
        to set an expiration time in days from today (if both are set, ``expires``
        is used).

        .. deprecated:: 6.3
           Keyword arguments are currently accepted case-insensitively.
           In Tornado 7.0 this will be changed to only accept lowercase
           arguments.
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: cookie, expires, cookies, days, datetime
- Signals: TF-IDF +0.029, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 27. pyg-team/pytorch_geometric :: Aggregation.forward  (`718273ac5378`)

Code diff:
```diff
- def forward(self, x: Tensor, index: Optional[Tensor] = None,
-                 ptr: Optional[Tensor] = None, dim_size: Optional[int] = None,
-                 dim: int = -2) -> Tensor:
+ def forward(
+         self,
+         x: Tensor,
+         index: Optional[Tensor] = None,
+         ptr: Optional[Tensor] = None,
+         dim_size: Optional[int] = None,
+         dim: int = -2,
+         max_num_elements: Optional[int] = None,
+     ) -> Tensor:
```

### Docstring before commit -> **inconclusive**
```text
r"""
        Args:
            x (torch.Tensor): The source tensor.
            index (torch.Tensor, optional): The indices of elements for
                applying the aggregation.
                One of :obj:`index` or :obj:`ptr` must be defined.
                (default: :obj:`None`)
            ptr (torch.Tensor, optional): If given, computes the aggregation
                based on sorted inputs in CSR representation.
                One of :obj:`index` or :obj:`ptr` must be defined.
                (default: :obj:`None`)
            dim_size (int, optional): The size of the output tensor at
                dimension :obj:`dim` after aggregation. (default: :obj:`None`)
            dim (int, optional): The dimension in which to aggregate.
                (default: :obj:`-2`)
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: ptr, dim, tensor, optional, index
- Signals: TF-IDF -0.005, encoder +0.011
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
r"""
        Args:
            x (torch.Tensor): The source tensor.
            index (torch.Tensor, optional): The indices of elements for
                applying the aggregation.
                One of :obj:`index` or :obj:`ptr` must be defined.
                (default: :obj:`None`)
            ptr (torch.Tensor, optional): If given, computes the aggregation
                based on sorted inputs in CSR representation.
                One of :obj:`index` or :obj:`ptr` must be defined.
                (default: :obj:`None`)
            dim_size (int, optional): The size of the output tensor at
                dimension :obj:`dim` after aggregation. (default: :obj:`None`)
            dim (int, optional): The dimension in which to aggregate.
                (default: :obj:`-2`)
            max_num_elements: (int, optional): The maximum number of elements
                within a single aggregation group. (default: :obj:`None`)
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: ptr, dim, tensor, elements, optional
- Signals: TF-IDF +0.052, encoder +0.011
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 28. cupy/cupy :: contraction  (`f93fb84e2371`)

Code diff:
```diff
+     mode_A = _auto_create_mode(A, mode_A)
+     mode_B = _auto_create_mode(B, mode_B)
+     mode_C = _auto_create_mode(C, mode_C)
-     if A.ndim != len(mode_A):
-         raise ValueError('ndim mismatch: {} != {}'.format(A.ndim, len(mode_A)))
-     if B.ndim != len(mode_B):
-         raise ValueError('ndim mismatch: {} != {}'.format(B.ndim, len(mode_B)))
-     if C.ndim != len(mode_C):
-         raise ValueError('ndim mismatch: {} != {}'.format(C.ndim, len(mode_C)))
-     alpha = numpy.array(alpha, compute_dtype)
+     alpha = numpy.asarray(alpha, compute_dtype)
-     beta = numpy.array(beta, compute_dtype)
+     beta = numpy.asarray(beta, compute_dtype)
```

### Docstring before commit -> **inconclusive**
```text
General tensor contraction

    This routine computes the tensor contraction:

        C = alpha * uop_A(A) * uop_B(B) + beta * uop_C(C)

    See cupy/cuda/cutensor.contraction for details.

    Args:
        alpha: Scaling factor for A * B.
        A (cupy.ndarray): Input tensor.
        desc_A (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor A.
        mode_A (tuple of int/str): A tuple that holds the labels of the modes
            of tensor A (e.g., if A_{x,y,z}, mode_A = {'x','y','z'})
        B (cupy.ndarray): Input tensor.
        desc_B (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor B.
        mode_B (tuple of int/str): A tuple that holds the labels of the modes
            of tensor B.
        beta: Scaling factor for C.
        C (cupy.ndarray): Input/output tensor.
        desc_C (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor C.
        mode_C (tuple of int/str): A tuple that holds the labels of the modes
            of tensor C.
        compute_dtype (numpy.dtype): Compute type for the intermediate
            computation.
        algo (cutenorAlgo_t): Allows users to select a specific algorithm.
            ALGO_DEFAULT lets the heuristic choose the algorithm.
            Any value >= 0 selects a specific GEMM-like algorithm and
            deactivates the heuristic. If a specified algorithm is not
            supported, STATUS_NOT_SUPPORTED is returned.
        ws_pref (cutensorWorksizePreference_t): User preference for the
            workspace of cuTensor.

    Returns:
        out (cupy.ndarray): Output tensor.

    Examples:
        See examples/cutensor/contraction.py
```
- Summary: The change does not clearly move the documentation's fit either way.
- Evidence [term_overlap]: Terms shared with the current code: contraction, desc, algo, beta, ws
- Signals: TF-IDF +0.020, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
General tensor contraction

    This routine computes the tensor contraction:

        C = alpha * uop_A(A) * uop_B(B) + beta * uop_C(C)

    See cupy/cuda/cutensor.contraction for details.

    Args:
        alpha (scalar or 0-dim numpy.ndarray): Scaling factor for A * B.
        A (cupy.ndarray): Input tensor.
        desc_A (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor A.
        mode_A (cutensor.Mode): A mode object created by `create_mode`.
        B (cupy.ndarray): Input tensor.
        desc_B (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor B.
        mode_B (cutensor.Mode): A mode object created by `create_mode`.
        beta (scalar or 0-dim numpy.ndarray): Scaling factor for C.
        C (cupy.ndarray): Input/output tensor.
        desc_C (class Descriptor): A descriptor that holds the information
            about the data type, modes, and strides of tensor C.
        mode_C (cutensor.Mode): A mode object created by `create_mode`.
        compute_dtype (numpy.dtype): Compute type for the intermediate
            computation.
        algo (cutenorAlgo_t): Allows users to select a specific algorithm.
            ALGO_DEFAULT lets the heuristic choose the algorithm.
            Any value >= 0 selects a specific GEMM-like algorithm and
            deactivates the heuristic. If a specified algorithm is not
            supported, STATUS_NOT_SUPPORTED is returned.
        ws_pref (cutensorWorksizePreference_t): User preference for the
            workspace of cuTensor.

    Returns:
        out (cupy.ndarray): Output tensor.

    Examples:
        See examples/cutensor/contraction.py
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: contraction, desc, algo, mode, beta
- Signals: TF-IDF +0.028, encoder +0.000
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

## 29. zulip/zulip :: StreamAdminTest.test_delete_streams_youre_not_on  (`78e30efa60ba`)

Code diff:
```diff
+         self.delete_stream(priv_stream)
- 
-         result = self.client_delete('/json/streams/' + str(priv_stream.id))
-         self.assert_json_error(result, "Invalid stream id")
```

### Docstring before commit -> **inconclusive**
```text
Administrators can delete public streams they aren't on, but cannot
        delete private streams they aren't on.
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: delete, streams, on
- Signals: TF-IDF -0.030, encoder +0.015
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **potential_drift**
```text
Administrators can delete public streams they aren't on, including
        private streams in their realm.
```
- Summary: The documentation matches the old code better than the new code.
- Evidence [term_overlap]: Terms shared with the current code: streams, delete, on
- Signals: TF-IDF -0.045, encoder +0.013
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Re-read the documentation against the new code and update the parts that describe old behaviour.

## 30. pandas-dev/pandas :: na_arithmetic_op  (`e6510d4afe27`)

Code diff:
```diff
- def na_arithmetic_op(left, right, op, str_rep: str):
+ def na_arithmetic_op(left, right, op, str_rep: Optional[str], is_cmp: bool = False):
+         if is_cmp:
+             # numexpr failed on comparison op, e.g. ndarray[float] > datetime
+             #  In this case we do not fall back to the masked op, as that
+             #  will handle complex numbers incorrectly, see GH#32047
+             raise
+     if is_cmp and (is_scalar(result) or result is NotImplemented):
+         # numpy returned a scalar instead of operating element-wise
+         # e.g. numeric array vs str
+         return invalid_comparison(left, right, op)
+ 
```

### Docstring before commit -> **inconclusive**
```text
Return the result of evaluating op on the passed in values.

    If native types are not compatible, try coersion to object dtype.

    Parameters
    ----------
    left : np.ndarray
    right : np.ndarray or scalar
    str_rep : str or None

    Returns
    -------
    array-like

    Raises
    ------
    TypeError : invalid operation
```
- Summary: The comparison signals disagree, so no finding is made.
- Evidence [term_overlap]: Terms shared with the current code: rep, op, right, left, scalar
- Signals: TF-IDF +0.033, encoder -0.035
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: Review manually: compare the documentation with the code diff.

### Docstring after commit -> **no_obvious_drift**
```text
Return the result of evaluating op on the passed in values.

    If native types are not compatible, try coersion to object dtype.

    Parameters
    ----------
    left : np.ndarray
    right : np.ndarray or scalar
    str_rep : str or None
    is_cmp : bool, default False
        If this a comparison operation.

    Returns
    -------
    array-like

    Raises
    ------
    TypeError : invalid operation
```
- Summary: No sign of drift: the documentation fits the new code at least as well as the old code.
- Evidence [term_overlap]: Terms shared with the current code: rep, op, comparison, right, left
- Signals: TF-IDF +0.102, encoder +0.085
- Uncertainty: Only this function and its documentation were inspected; callers, runtime behaviour and other documentation were not.
- Uncertainty: Similarity signals measure shared words or meaning, not correctness.
- Uncertainty: Some input was longer than the encoder limit and was truncated.
- Next step: No action suggested; a quick skim is still worthwhile for behavioural changes.

