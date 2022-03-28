var currentCards = []

function registerCardListeners() {
  $(".usercard").dblclick(function() {
      $(this).toggleClass("flip")
      $(this).find('.front').toggleClass('d-none')
      $(this).find('.back').toggleClass('d-none')
    })
    $('.usercard').draggable({
      revert: "invalid",
      helper: function(event) {
        let el = $(event.currentTarget)
        let icon = $($(event.currentTarget)).clone()
        $(icon).height(el.height())
        $(icon).width(el.width())
        return icon
      }
    })
  $('.droppable').droppable({
    drop: function(event, ui) {
      let newid = ui.draggable[0].id
      if ((currentCards.length == 0) || (!(currentCards.includes(newid)))) {
        currentCards.push(newid)
        $('#cardsindeck').val(JSON.stringify(currentCards))
        $('#nCards').text(currentCards.length)
      }
    }
  })
}

// Mount cards
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
      this.current_user.cards.forEach((card) => {
        card.orgid = card.id
        card.id = ""
        card.id = "usercard-" + card.orgid
        card.src = `/upload/${card.image}?auth_token=${this.token}`
        card.imgid = "card-" + card.orgid
      })
    })
  },
  updated() {
    registerCardListeners()
  }
}).mount('.cardcol')
