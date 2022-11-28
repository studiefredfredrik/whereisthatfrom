<script>
  import ProgressBar from 'svelte-progress-bar'
  import axios from 'axios'

  let search = ''
  let hasSearched = false
  let loading = false
  let results = []
  let isLoadingClip = false
  let generatedClipUrl = ''
  let generatedVttUrl = ''

  const progress = new ProgressBar({ target: document.querySelector('body'), props: { color: '#888', intervalTime: 300 } })

  const getSearchResultsFromServer = async (search) => {
      if(loading) return;
      loading = true
      try {
          let res = await axios.get(`/api/search/${search}`)
          results = res.data.results
          console.log(JSON.stringify(results))
          hasSearched = true
      } catch (ex){
        console.error(ex)
      }
      loading = false

  }

  const getFindResultFromServer = async (movieName, timestamp) => {
      if(loading) return;
      loading = true
      try {
          let res = await axios.get(`/api/find/${movieName}/${timestamp}`)
          results = res.data.results
          console.log(JSON.stringify(results))
          hasSearched = true
      } catch (ex){
          console.error(ex)
      }
      loading = false
  }

  const generateClip = async (movieName, timestamp) => {
      if(isLoadingClip) return;
      isLoadingClip = true
      progress.start()
      try {
          let res = await axios.get(`/api/video/${movieName}/${timestamp}`)
          generatedVttUrl = res.data.new_subtitle_path
          generatedClipUrl = res.data.new_movie_path

      } catch (ex){
          console.error(ex)
      }
      isLoadingClip = false
      progress.complete()
  }

</script>

<main>
  <video buffered controls src="generated/test-out.mp4"></video>
  <h1>Where is that from?</h1>
  <h4>Helping you find where that movie quote is from</h4>
  <div class="card">
    <input type="text" bind:value={search} on:keydown={(event) => { if(event.key === 'Enter') getSearchResultsFromServer(search) }    }>
    <button on:click="{getSearchResultsFromServer(search)}">
      Search
    </button>
  </div>
  {#if isLoadingClip}
    <div class="card" >
      <h3>Loading clip...</h3>
    </div>
  {/if}
  {#if !isLoadingClip && generatedClipUrl}
    <div class="card video-container">
      <video controls>
        <source src="{generatedClipUrl}" type="video/mp4">
        <track default src="{generatedVttUrl}" kind="subtitles" srclang="en" label="English">
      </video>
    </div>
  {/if}
  {#if hasSearched && !loading && results.length > 0}
    <div class="card" >
      <h4>Results</h4>
      <table class="result-table">
        <tr>
          <th>Movie name</th>
          <th>Timestamp</th>
          <th>Subtitle text</th>
          <th>Actions</th>
        </tr>
        {#each results as { movie_file_name, timestamp_text_start, text_lines } , index (index)}
          <tr on:click="{getFindResultFromServer(movie_file_name, timestamp_text_start)}">
            <td>{ movie_file_name }</td>
            <td>{ timestamp_text_start }</td>
            <td>{ text_lines }</td>
            <td><button on:click|stopPropagation="{generateClip(movie_file_name, timestamp_text_start)}">Watch clip</button></td>
          </tr>
        {/each}
      </table>
    </div>
  {/if}
  {#if hasSearched && !loading && results.length === 0}
    <div class="card" >
      <h3>No results found for that search...</h3>
    </div>
  {/if}
  {#if loading}
    <div class="card" >
      <h3>Loading...</h3>
    </div>
  {/if}

  <p class="bottom-text">
    <a class="subtext" href="https://github.com/studiefredfredrik/whereisthatfrom">Check out the GitHub repo</a>
  </p>
</main>

<style>
  .result-table{
    border-spacing: 20px 0;
  }
  .result-table th {
    margin-left: 10px;
    text-align: left;
  }
  .result-table td {
    margin-left: 10px;
    text-align: left;
  }
  .bottom-text{
    margin-top: 100px;
  }
  .subtext {
    color: #888;
  }

  VIDEO {
    max-height: 300px;
  }
  .video-container{
    position: sticky;
    top: 10px;
  }

  ::cue {
    color: #ccc;
    background: none;
  }

</style>
