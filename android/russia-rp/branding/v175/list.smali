.method private final buildServerList()V
    .locals 7
    invoke-static {}, Lcom/wn/blackrussia/game/Multiplayer;->getInstance()Lcom/wn/blackrussia/game/Multiplayer;
    move-result-object v0
    invoke-static {v0}, Landroid/view/LayoutInflater;->from(Landroid/content/Context;)Landroid/view/LayoutInflater;
    move-result-object v0
    invoke-virtual {p0}, Lcom/wn/blackrussia/game/ui/BrChooseServer;->getBinding()Landroidx/viewbinding/ViewBinding;
    move-result-object v1
    check-cast v1, Lcom/wn/blackrussia/databinding/BrServerselectBinding;
    iget-object v1, v1, Lcom/wn/blackrussia/databinding/BrServerselectBinding;->scrollLayoutServers:Landroid/widget/LinearLayout;
    invoke-virtual {v1}, Landroid/widget/LinearLayout;->removeAllViews()V
    invoke-direct {p0}, Lcom/wn/blackrussia/game/ui/BrChooseServer;->getServers()Ljava/util/List;
    move-result-object v2
    invoke-interface {v2}, Ljava/util/List;->size()I
    move-result v2
    const/4 v3, 0
    const/4 v4, 0
    :next
    if-ge v3, v2, :done
    sget v5, Lcom/wn/blackrussia/R$layout;->br_serverselect_server:I
    invoke-virtual {v0, v5, v1, v4}, Landroid/view/LayoutInflater;->inflate(ILandroid/view/ViewGroup;Z)Landroid/view/View;
    move-result-object v5
    new-instance v6, Lcom/wn/blackrussia/game/ui/BrChooseServer$$ExternalSyntheticLambda5;
    invoke-direct {v6, p0, v3}, Lcom/wn/blackrussia/game/ui/BrChooseServer$$ExternalSyntheticLambda5;-><init>(Lcom/wn/blackrussia/game/ui/BrChooseServer;I)V
    invoke-virtual {v5, v6}, Landroid/view/View;->setOnClickListener(Landroid/view/View$OnClickListener;)V
    invoke-direct {p0, v5, v3}, Lcom/wn/blackrussia/game/ui/BrChooseServer;->bindServerCard(Landroid/view/View;I)V
    invoke-virtual {v1, v5}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V
    add-int/lit8 v3, v3, 1
    goto :next
    :done
    return-void
.end method
