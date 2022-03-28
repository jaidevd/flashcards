// Mount decklist
Vue.createApp({
  data() {
    return {
      token: window.localStorage.getItem('flashcard-token'),
      current_user: {}
    }
  },
  mounted() {
    fetch("http://localhost:5000/user?auth_token=" + this.token).then((resp) => {
      if (resp.ok) {
        return resp.json()
      }
    }).then((data) => {
      this.current_user = data
      this.current_user.decks.forEach((deck) => {
        deck.deck_url = `/deck/${deck.id}?auth_token=` + this.token
        deck.del_id = `deldeck-${deck.id}`
      })
    })
  }
}).mount('#decklist')
